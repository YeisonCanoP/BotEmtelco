"""
DTOs utilizados para consultas y actualizaciones de pedidos.

Este módulo define los modelos de entrada y salida usados por las herramientas
o servicios relacionados con pedidos.

Las entradas no reciben la identificación del cliente. La identificación debe
obtenerse exclusivamente desde el cliente verificado en `ConversationContext`.
Esto evita que el modelo de lenguaje pueda consultar o modificar pedidos de un
cliente diferente al validado en la sesión.

Responsabilidades principales:

- Validar entradas para listar pedidos.
- Validar entradas para consultar un pedido específico.
- Validar entradas para actualizar una dirección de entrega.
- Exponer respuestas seguras para el agente.
- Garantizar consistencia entre banderas como `success`, `found`, `updated` y
  los datos retornados.

"""

from datetime import date
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.entities import OrderStatus


class CustomerOrdersInputDTO(BaseModel):
    """
    Entrada para listar los pedidos del cliente verificado.

    Este DTO no contiene campos porque el cliente no debe ser recibido como
    argumento del modelo de lenguaje. La herramienta responsable debe tomar la
    identificación desde `ConversationContext`, siempre que exista un cliente
    previamente verificado.

    Attributes:
        model_config: Configuración que impide recibir campos adicionales.
    """

    model_config = ConfigDict(extra="forbid")


class OrderLookupInputDTO(BaseModel):
    """
    Entrada para consultar un pedido específico.

    Este DTO recibe únicamente el número del pedido. No recibe identificación
    del cliente porque esa información se toma del contexto conversacional
    validado.

    Attributes:
        order_number: Número del pedido que se desea consultar.
    """

    model_config = ConfigDict(extra="forbid")

    order_number: str = Field(
        min_length=1,
        max_length=30,
        pattern=r"^[A-Z0-9-]+$",
        description=(
            "Número del pedido. Ejemplo: ORD-1001. No envíes la identificación del cliente."
        ),
    )

    @field_validator("order_number")
    @classmethod
    def normalize_order_number(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza el número del pedido.

        Elimina espacios al inicio y al final, y convierte el valor a
        mayúsculas para evitar diferencias por formato ingresado por el usuario.

        Args:
            value: Número de pedido recibido desde la entrada.

        Returns:
            Número de pedido normalizado.
        """

        return value.strip().upper()


class UpdateOrderAddressInputDTO(OrderLookupInputDTO):
    """
    Entrada para actualizar la dirección de entrega de un pedido.

    Extiende `OrderLookupInputDTO` porque para actualizar una dirección también
    se requiere identificar el pedido. La identificación del cliente sigue sin
    recibirse por argumentos y debe tomarse desde `ConversationContext`.

    Attributes:
        order_number: Número del pedido que se desea actualizar.
        new_address: Nueva dirección completa de entrega.
    """

    new_address: str = Field(
        min_length=5,
        max_length=250,
        description="Nueva dirección completa de entrega.",
    )

    @field_validator("new_address")
    @classmethod
    def normalize_address(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza la dirección de entrega.

        Elimina espacios duplicados, espacios iniciales y espacios finales para
        guardar una dirección más limpia.

        Args:
            value: Dirección recibida desde la entrada.

        Returns:
            Dirección normalizada.
        """

        return " ".join(value.split())


class OrderSummaryDTO(BaseModel):
    """
    Resumen seguro de un pedido.

    Este DTO se usa al listar pedidos de un cliente. No incluye `customer_id` ni
    dirección porque el listado general solo necesita mostrar información
    básica del pedido.

    Attributes:
        id: Número único del pedido.
        status: Estado actual del pedido.
        estimated_delivery: Fecha estimada de entrega, si existe.
    """

    id: str = Field(
        min_length=1,
        max_length=30,
    )

    status: OrderStatus

    estimated_delivery: date | None = None


class OrderDetailDTO(OrderSummaryDTO):
    """
    Detalle de un pedido perteneciente al cliente verificado.

    Este DTO se usa cuando el usuario consulta un pedido específico o cuando se
    actualiza correctamente la dirección de entrega.

    A diferencia del resumen, incluye la dirección porque en estos flujos el
    usuario está trabajando sobre un pedido concreto ya validado contra el
    cliente de la sesión.

    Attributes:
        id: Número único del pedido.
        status: Estado actual del pedido.
        estimated_delivery: Fecha estimada de entrega, si existe.
        address: Dirección de entrega asociada al pedido.
    """

    address: str = Field(
        min_length=1,
        max_length=250,
    )


class CustomerOrdersResultDTO(BaseModel):
    """
    Resultado de listar los pedidos del cliente verificado.

    Este DTO representa tanto consultas exitosas como casos en los que no existe
    un cliente validado en la conversación.

    Attributes:
        success: Indica si la operación se ejecutó correctamente.
        requires_customer_verification: Indica si primero debe validarse un
            cliente.
        found: Indica si se encontraron pedidos.
        count: Cantidad de pedidos retornados.
        orders: Lista de pedidos resumidos.
    """

    success: bool

    requires_customer_verification: bool = False

    found: bool

    count: int = Field(
        ge=0,
    )

    orders: list[OrderSummaryDTO] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba la consistencia del resultado del listado.

        Reglas de consistencia:

        - Si falta verificar el cliente, la operación no puede ser exitosa.
        - Si falta verificar el cliente, no pueden retornarse pedidos.
        - Si la operación es exitosa, `count` debe coincidir con la cantidad de
          elementos en `orders`.
        - Si la operación es exitosa, `found` debe indicar si la lista contiene
          pedidos.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.requires_customer_verification:
            if self.success:
                raise ValueError("Una consulta sin cliente verificado no puede ser exitosa")

            if self.found or self.count != 0 or self.orders:
                raise ValueError("Una consulta sin verificar no puede retornar pedidos")

        if self.success:
            if self.count != len(self.orders):
                raise ValueError("count debe coincidir con la cantidad de pedidos")

            if self.found != bool(self.orders):
                raise ValueError("found debe indicar si la lista contiene pedidos")

        return self


class OrderLookupResultDTO(BaseModel):
    """
    Resultado de consultar un pedido específico.

    Este DTO representa la consulta de un pedido particular perteneciente al
    cliente verificado. También permite informar que primero se requiere validar
    el cliente antes de consultar información del pedido.

    Attributes:
        success: Indica si la operación se ejecutó correctamente.
        requires_customer_verification: Indica si primero debe validarse un
            cliente.
        found: Indica si el pedido fue encontrado.
        order: Detalle del pedido encontrado, si aplica.
    """

    success: bool

    requires_customer_verification: bool = False

    found: bool

    order: OrderDetailDTO | None = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba la consistencia del resultado de consulta.

        Reglas de consistencia:

        - Si falta verificar el cliente, la operación no puede ser exitosa.
        - Si falta verificar el cliente, no puede retornarse un pedido.
        - Si `found` es `True`, debe existir información en `order`.
        - Si `found` es `False`, `order` debe ser `None`.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.requires_customer_verification:
            if self.success or self.found or self.order is not None:
                raise ValueError("Una consulta sin verificar no puede retornar un pedido")

        if self.found and self.order is None:
            raise ValueError("Un pedido encontrado debe incluir información")

        if not self.found and self.order is not None:
            raise ValueError("Un pedido no encontrado no puede incluir información")

        return self


OrderAddressFailureReason = Literal[
    "CUSTOMER_NOT_VERIFIED",
    "ORDER_NOT_FOUND_OR_NOT_OWNED",
    "STATUS_NOT_UPDATABLE",
]


class OrderAddressUpdateResultDTO(BaseModel):
    """
    Resultado de actualizar la dirección de un pedido.

    Este DTO representa una actualización exitosa o un fallo controlado. Cuando
    la actualización falla, se debe indicar el motivo mediante `reason`.

    Attributes:
        success: Indica si la operación terminó exitosamente.
        updated: Indica si la dirección fue actualizada.
        reason: Motivo por el cual no se realizó la actualización.
        order: Pedido actualizado, si la operación fue exitosa.
    """

    success: bool

    updated: bool

    reason: OrderAddressFailureReason | None = None

    order: OrderDetailDTO | None = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba la consistencia del resultado de actualización.

        Reglas de consistencia:

        - Si `updated` es `True`, `success` también debe ser `True`.
        - Si `updated` es `True`, debe existir un pedido en `order`.
        - Si `updated` es `True`, no debe existir motivo de fallo.
        - Si `updated` es `False`, `success` también debe ser `False`.
        - Si `updated` es `False`, debe existir un motivo en `reason`.
        - Si `updated` es `False`, no debe retornarse un pedido.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.updated:
            if not self.success:
                raise ValueError("Una actualización realizada debe ser exitosa")

            if self.order is None:
                raise ValueError("Una actualización realizada debe incluir el pedido")

            if self.reason is not None:
                raise ValueError("Una actualización realizada no puede tener motivo de fallo")

        if not self.updated:
            if self.success:
                raise ValueError("Una actualización no realizada no puede ser exitosa")

            if self.reason is None:
                raise ValueError("Una actualización no realizada debe indicar el motivo")

            if self.order is not None:
                raise ValueError("Una actualización fallida no debe retornar el pedido")

        return self
