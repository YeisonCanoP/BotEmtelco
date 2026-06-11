"""
Herramientas para consultar y actualizar pedidos.

Este módulo contiene las herramientas que el modelo de lenguaje puede invocar
para consultar pedidos del cliente verificado y actualizar direcciones de
entrega cuando el estado del pedido lo permite.

Responsabilidades principales:

- Listar pedidos del cliente verificado.
- Consultar el estado, fecha estimada y dirección de un pedido específico.
- Actualizar la dirección de entrega de pedidos modificables.
- Registrar acciones pendientes cuando falta validar al cliente.
- Limpiar acciones pendientes cuando la operación se completa.
- Retornar DTOs estructurados para que el agente genere una respuesta natural.
"""

from app.application.dtos import (
    CustomerOrdersInputDTO,
    CustomerOrdersResultDTO,
    OrderAddressUpdateResultDTO,
    OrderDetailDTO,
    OrderLookupInputDTO,
    OrderLookupResultDTO,
    OrderSummaryDTO,
    PendingAction,
    UpdateOrderAddressInputDTO,
)
from app.application.ports.repositories import OrderRepository
from app.application.services.conversation_context import ConversationContext
from app.application.tools.base import Tool
from app.domain.entities import Order, OrderStatus

UPDATABLE_ORDER_STATUSES = frozenset(
    {
        OrderStatus.CONFIRMED,
        OrderStatus.PREPARING,
    }
)


def order_to_summary_dto(
    order: Order,
) -> OrderSummaryDTO:
    """
    Convierte una entidad de pedido en un resumen seguro.

    Este resumen se usa al listar pedidos del cliente. No incluye la
    identificación del cliente ni la dirección de entrega porque esa información
    no es necesaria para un listado general.

    Args:
        order: Entidad de dominio del pedido.

    Returns:
        DTO con número de pedido, estado y fecha estimada de entrega.
    """

    return OrderSummaryDTO(
        id=order.id,
        status=order.status,
        estimated_delivery=order.estimated_delivery,
    )


def order_to_detail_dto(
    order: Order,
) -> OrderDetailDTO:
    """
    Convierte una entidad de pedido en un detalle seguro.

    Este detalle se usa cuando el usuario consulta un pedido específico o cuando
    se actualiza correctamente la dirección de entrega.

    Args:
        order: Entidad de dominio del pedido validado contra el cliente actual.

    Returns:
        DTO con número de pedido, estado, fecha estimada y dirección de entrega.
    """

    return OrderDetailDTO(
        id=order.id,
        status=order.status,
        estimated_delivery=order.estimated_delivery,
        address=order.address,
    )


def clear_matching_pending_action(
    context: ConversationContext,
    action: PendingAction,
    reference: str | None = None,
) -> None:
    """
    Limpia una acción pendiente cuando coincide con la operación completada.

    Este helper evita borrar acciones pendientes que no pertenecen al flujo
    actual. Si se recibe una referencia, también debe coincidir con la referencia
    almacenada en la conversación.

    Args:
        context: Contexto mutable de la conversación actual.
        action: Acción pendiente que se espera limpiar.
        reference: Referencia asociada a la acción, por ejemplo un número de
            pedido. Si es `None`, solo se valida la acción.
    """

    conversation = context.conversation

    if conversation.pending_action is not action:
        return

    if reference is not None and conversation.pending_reference != reference:
        return

    context.clear_pending_action()


class ListCustomerOrdersTool(
    Tool[
        CustomerOrdersInputDTO,
        CustomerOrdersResultDTO,
    ]
):
    """
    Herramienta para listar los pedidos del cliente verificado.

    Si todavía no existe un cliente verificado en la sesión, la herramienta
    registra una acción pendiente `LIST_ORDERS` y retorna un resultado indicando
    que primero debe validarse el cliente.
    """

    name = "list_customer_orders"

    description = """Lista los pedidos del cliente verificado en la sesión. 
        La herramienta no recibe identificación. 
        Si el cliente todavía no está verificado, indicará que primero debes 
        solicitar su identificación y usar find_customer."""

    def __init__(
        self,
        repository: OrderRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta.

        Args:
            repository: Repositorio usado para consultar pedidos.
            conversation_context: Contexto de la conversación actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[CustomerOrdersInputDTO]:
        """
        Retorna el modelo de entrada de la herramienta.

        Returns:
            DTO vacío, porque la herramienta obtiene el cliente desde el
            contexto conversacional.
        """

        return CustomerOrdersInputDTO

    async def execute(
        self,
        arguments: CustomerOrdersInputDTO,
    ) -> CustomerOrdersResultDTO:
        """
        Lista los pedidos asociados al cliente verificado.

        Si no hay cliente verificado, no consulta el repositorio y deja la
        acción pendiente para retomarla después de ejecutar `find_customer`.

        Args:
            arguments: Entrada vacía validada por el registro de herramientas.

        Returns:
            Resultado estructurado con la lista de pedidos o la indicación de
            que primero se requiere verificar el cliente.

        Raises:
            RepositoryError: Si ocurre un fallo al consultar los pedidos.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.set_pending_action(PendingAction.LIST_ORDERS)

            return CustomerOrdersResultDTO(
                success=False,
                requires_customer_verification=True,
                found=False,
                count=0,
                orders=[],
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return CustomerOrdersResultDTO(
                success=False,
                requires_customer_verification=True,
                found=False,
                count=0,
                orders=[],
            )

        orders = await self._repository.list_by_customer(customer_id)

        results = [order_to_summary_dto(order) for order in orders]

        clear_matching_pending_action(
            context=self._conversation_context,
            action=PendingAction.LIST_ORDERS,
        )

        return CustomerOrdersResultDTO(
            success=True,
            requires_customer_verification=False,
            found=bool(results),
            count=len(results),
            orders=results,
        )


class GetCustomerOrderTool(
    Tool[
        OrderLookupInputDTO,
        OrderLookupResultDTO,
    ]
):
    """
    Herramienta para consultar un pedido del cliente verificado.

    La herramienta recibe únicamente el número del pedido. La identificación del
    cliente se toma desde `ConversationContext` y se usa para validar que el
    pedido pertenece al cliente actual.

    Si no hay cliente verificado, registra una acción pendiente
    `GET_ORDER_STATUS` junto con el número de pedido.
    """

    name = "get_customer_order"

    description = """Consulta el estado, fecha estimada y dirección de un pedido específico. 
        Solo puede consultar pedidos pertenecientes al cliente verificado. 
        Recibe únicamente el número del pedido, nunca la identificación."""

    def __init__(
        self,
        repository: OrderRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta.

        Args:
            repository: Repositorio usado para consultar pedidos.
            conversation_context: Contexto de la conversación actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[OrderLookupInputDTO]:
        """
        Retorna el modelo de entrada para consultar un pedido.

        Returns:
            DTO que recibe únicamente el número del pedido.
        """

        return OrderLookupInputDTO

    async def execute(
        self,
        arguments: OrderLookupInputDTO,
    ) -> OrderLookupResultDTO:
        """
        Consulta un pedido filtrando por número y cliente verificado.

        Si el cliente no está verificado, no consulta el repositorio y deja la
        consulta como acción pendiente.

        Args:
            arguments: DTO con el número de pedido normalizado.

        Returns:
            Resultado estructurado con el pedido encontrado, o una respuesta
            indicando que no existe, no pertenece al cliente o requiere
            verificación previa.

        Raises:
            RepositoryError: Si ocurre un fallo al consultar el pedido.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.set_pending_action(
                action=PendingAction.GET_ORDER_STATUS,
                reference=arguments.order_number,
            )

            return OrderLookupResultDTO(
                success=False,
                requires_customer_verification=True,
                found=False,
                order=None,
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return OrderLookupResultDTO(
                success=False,
                requires_customer_verification=True,
                found=False,
                order=None,
            )

        order = await self._repository.get_by_number_and_customer(
            order_number=arguments.order_number,
            customer_identification=customer_id,
        )

        if order is None:
            return OrderLookupResultDTO(
                success=True,
                requires_customer_verification=False,
                found=False,
                order=None,
            )

        clear_matching_pending_action(
            context=self._conversation_context,
            action=PendingAction.GET_ORDER_STATUS,
            reference=arguments.order_number,
        )

        return OrderLookupResultDTO(
            success=True,
            requires_customer_verification=False,
            found=True,
            order=order_to_detail_dto(order),
        )


class UpdateOrderAddressTool(
    Tool[
        UpdateOrderAddressInputDTO,
        OrderAddressUpdateResultDTO,
    ]
):
    """
    Herramienta para actualizar la dirección de entrega de un pedido.

    La herramienta solo puede modificar pedidos pertenecientes al cliente
    verificado y únicamente cuando el pedido está en un estado permitido.

    Estados modificables:

    - `CONFIRMED`
    - `PREPARING`

    Si no hay cliente verificado, registra una acción pendiente
    `UPDATE_ORDER_ADDRESS` asociada al número de pedido.
    """

    name = "update_order_address"

    description = """Actualiza la dirección de entrega de un pedido perteneciente al cliente 
        verificado. Solo se permite para pedidos en estado CONFIRMED o PREPARING. 
        Recibe el número del pedido y la nueva dirección. 
        Nunca recibe la identificación del cliente."""

    def __init__(
        self,
        repository: OrderRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta.

        Args:
            repository: Repositorio usado para consultar y actualizar pedidos.
            conversation_context: Contexto de la conversación actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[UpdateOrderAddressInputDTO]:
        """
        Retorna el modelo de entrada para actualizar direcciones.

        Returns:
            DTO con número de pedido y nueva dirección de entrega.
        """

        return UpdateOrderAddressInputDTO

    async def execute(
        self,
        arguments: UpdateOrderAddressInputDTO,
    ) -> OrderAddressUpdateResultDTO:
        """
        Actualiza la dirección de un pedido validando cliente, propiedad y estado.

        El flujo realiza estas comprobaciones:

        - Verifica que exista un cliente validado en la conversación.
        - Consulta el pedido validando que pertenezca a ese cliente.
        - Comprueba que el estado permita modificar la dirección.
        - Ejecuta la actualización en el repositorio.
        - Limpia la acción pendiente si la actualización se completa.

        Args:
            arguments: DTO con número de pedido y nueva dirección normalizada.

        Returns:
            Resultado estructurado de la actualización. Si falla, incluye un
            motivo controlado.

        Raises:
            RepositoryError: Si ocurre un fallo al consultar o actualizar el
                pedido.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.set_pending_action(
                action=PendingAction.UPDATE_ORDER_ADDRESS,
                reference=arguments.order_number,
            )

            return OrderAddressUpdateResultDTO(
                success=False,
                updated=False,
                reason="CUSTOMER_NOT_VERIFIED",
                order=None,
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return OrderAddressUpdateResultDTO(
                success=False,
                updated=False,
                reason="CUSTOMER_NOT_VERIFIED",
                order=None,
            )

        existing_order = await self._repository.get_by_number_and_customer(
            order_number=arguments.order_number,
            customer_identification=customer_id,
        )

        if existing_order is None:
            return OrderAddressUpdateResultDTO(
                success=False,
                updated=False,
                reason="ORDER_NOT_FOUND_OR_NOT_OWNED",
                order=None,
            )

        if existing_order.status not in UPDATABLE_ORDER_STATUSES:
            return OrderAddressUpdateResultDTO(
                success=False,
                updated=False,
                reason="STATUS_NOT_UPDATABLE",
                order=None,
            )

        updated_order = await self._repository.update_delivery_address(
            order_number=arguments.order_number,
            customer_identification=customer_id,
            new_address=arguments.new_address,
        )

        if updated_order is None:
            # El estado pudo cambiar entre la consulta y el UPDATE condicionado.
            return OrderAddressUpdateResultDTO(
                success=False,
                updated=False,
                reason="STATUS_NOT_UPDATABLE",
                order=None,
            )

        clear_matching_pending_action(
            context=self._conversation_context,
            action=PendingAction.UPDATE_ORDER_ADDRESS,
            reference=arguments.order_number,
        )

        return OrderAddressUpdateResultDTO(
            success=True,
            updated=True,
            reason=None,
            order=order_to_detail_dto(updated_order),
        )
