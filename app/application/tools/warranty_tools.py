"""
Herramientas para consultar garantías, registrar reclamos y escalar tickets.

Este módulo define las herramientas de aplicación utilizadas por el agente
conversacional para atender casos de postventa relacionados con garantías y
soporte técnico.

Las herramientas permiten:

    - Consultar la cobertura de garantía de un producto comprado.
    - Registrar un reclamo técnico cuando la garantía está vigente.
    - Generar un ticket de soporte asociado al reclamo.
    - Escalar un ticket existente a atención humana.

Regla de seguridad:
    La identificación del cliente nunca se recibe como argumento del modelo de
    lenguaje. Siempre se obtiene desde `ConversationContext`, después de que el
    cliente ha sido verificado en la conversación.

Esto evita que el agente consulte, cree o escale reclamos usando una
identificación inventada, manipulada o perteneciente a otro cliente.

Este módulo pertenece a la capa de aplicación. Coordina DTOs, contexto
conversacional, entidades de dominio y repositorios, pero no accede directamente
a SQLAlchemy ni a detalles concretos de infraestructura.
"""

from datetime import date
from uuid import uuid4

from app.application.dtos import (
    PendingAction,
    WarrantyClaimCreateInputDTO,
    WarrantyClaimCreateResultDTO,
    WarrantyClaimDTO,
    WarrantyClaimEscalateInputDTO,
    WarrantyClaimEscalationResultDTO,
    WarrantyLookupInputDTO,
    WarrantyLookupReason,
    WarrantyLookupResultDTO,
    WarrantySummaryDTO,
)
from app.application.ports.repositories import WarrantyRepository
from app.application.services.conversation_context import ConversationContext
from app.application.tools.base import Tool
from app.domain.entities import (
    Warranty,
    WarrantyClaim,
    WarrantyClaimStatus,
)


def warranty_to_summary_dto(
    warranty: Warranty,
    reference_date: date,
) -> WarrantySummaryDTO:
    """
    Convierte una garantía de dominio en un resumen seguro.

    El resumen contiene únicamente la información necesaria para que el agente
    pueda responder al cliente sin exponer detalles internos del sistema.

    El campo `covered` se calcula con una fecha de referencia explícita. Esto
    permite evaluar la vigencia de forma determinista y evita que el modelo de
    lenguaje decida por sí mismo si una garantía cubre o no cubre el producto.

    Args:
        warranty: Garantía obtenida desde el repositorio.
        reference_date: Fecha usada para calcular la cobertura.

    Returns:
        DTO serializable con el resumen de la garantía.
    """

    return WarrantySummaryDTO(
        id=warranty.id,
        product_sku=warranty.product_sku,
        order_id=warranty.order_id,
        active=warranty.active,
        starts_on=warranty.starts_on,
        expires_on=warranty.expires_on,
        covered=warranty.is_valid_on(reference_date),
    )


def claim_to_dto(
    claim: WarrantyClaim,
) -> WarrantyClaimDTO:
    """
    Convierte un reclamo de dominio en un DTO seguro.

    Esta función separa la entidad de dominio del objeto que se devuelve desde
    la herramienta. El DTO resultante contiene la información necesaria para que
    el agente informe el estado del ticket al cliente.

    Args:
        claim: Reclamo técnico representado como entidad de dominio.

    Returns:
        DTO serializable con la información pública del reclamo.
    """

    return WarrantyClaimDTO(
        id=claim.id,
        warranty_id=claim.warranty_id,
        description=claim.description,
        status=claim.status,
        requires_human=claim.requires_human,
        escalation_reason=claim.escalation_reason,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
    )


def generate_claim_id() -> str:
    """
    Genera un identificador único para el reclamo y ticket técnico.

    El identificador del reclamo funciona también como número de ticket. Se usa
    el prefijo `CLM` para diferenciar estos casos de otros identificadores del
    sistema.

    Returns:
        Identificador con formato `CLM-{UUID_HEXADECIMAL}`.
    """

    return f"CLM-{uuid4().hex.upper()}"


def clear_pending_warranty_action(
    context: ConversationContext,
    action: PendingAction,
) -> None:
    """
    Limpia una acción pendiente únicamente cuando coincide con la esperada.

    Esta función evita borrar accidentalmente una acción pendiente distinta. Por
    ejemplo, si el usuario está completando un flujo de reclamo, no se debe
    limpiar esa acción desde otro flujo de garantía que no corresponde.

    Args:
        context: Contexto conversacional de la sesión actual.
        action: Acción pendiente que se espera limpiar.
    """

    if context.conversation.pending_action is action:
        context.clear_pending_action()


def get_coverage_failure_reason(
    warranty: Warranty,
    reference_date: date,
) -> WarrantyLookupReason | None:
    """
    Determina por qué una garantía no está vigente.

    La evaluación se realiza con reglas deterministas del dominio, sin depender
    del modelo de lenguaje. Esto evita respuestas inventadas sobre cobertura,
    fechas o estado administrativo de la garantía.

    Args:
        warranty: Garantía que se desea evaluar.
        reference_date: Fecha usada para validar la cobertura.

    Returns:
        Código de razón cuando la garantía no cubre el producto, o None cuando
        la garantía está vigente.
    """

    if not warranty.active:
        return "WARRANTY_NOT_ACTIVE"

    if reference_date < warranty.starts_on:
        return "WARRANTY_NOT_STARTED"

    if reference_date > warranty.expires_on:
        return "WARRANTY_EXPIRED"

    return None


class CheckWarrantyTool(
    Tool[
        WarrantyLookupInputDTO,
        WarrantyLookupResultDTO,
    ]
):
    """
    Herramienta para consultar la cobertura de garantía de un producto comprado.

    Esta herramienta valida que exista un cliente verificado en el contexto
    conversacional antes de consultar información de garantías.

    Casos principales que maneja:
        - El cliente aún no está verificado.
        - El pedido no existe o no tiene garantías asociadas.
        - El pedido contiene varios productos con garantía y se requiere
          selección de producto.
        - Existe una garantía específica y se debe evaluar si está vigente.

    La identificación del cliente nunca se recibe desde el LLM. Se obtiene
    exclusivamente desde `ConversationContext`.
    """

    name = "check_warranty"

    description = (
        "Consulta la garantía de un producto perteneciente al cliente "
        "verificado. Recibe el número del pedido y opcionalmente el SKU. "
        "Nunca recibe la identificación del cliente. Si el pedido contiene "
        "varios productos con garantía, retorna las opciones para que el "
        "usuario seleccione el producto correcto."
    )

    def __init__(
        self,
        repository: WarrantyRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta de consulta de garantías.

        Args:
            repository: Puerto usado para consultar garantías y reclamos.
            conversation_context: Contexto conversacional de la sesión actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[WarrantyLookupInputDTO]:
        """
        Retorna el DTO de entrada esperado por la herramienta.

        Returns:
            Clase DTO usada para validar los argumentos de entrada.
        """

        return WarrantyLookupInputDTO

    async def execute(
        self,
        arguments: WarrantyLookupInputDTO,
    ) -> WarrantyLookupResultDTO:
        """
        Consulta y evalúa la cobertura de una garantía.

        Si el cliente no está verificado, guarda los datos de la consulta en el
        contexto conversacional para continuar el flujo después de la
        verificación.

        Si el SKU no se proporciona y el pedido tiene varias garantías, retorna
        las opciones disponibles para que el usuario seleccione el producto
        correcto.

        Args:
            arguments: Datos necesarios para consultar la garantía.

        Returns:
            Resultado estructurado de la consulta de garantía.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.remember_warranty_lookup(
                order_number=arguments.order_number,
                product_sku=arguments.product_sku,
            )

            return WarrantyLookupResultDTO(
                success=False,
                found=False,
                covered=False,
                requires_customer_verification=True,
                requires_product_selection=False,
                reason="CUSTOMER_NOT_VERIFIED",
                warranty=None,
                warranties=[],
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return WarrantyLookupResultDTO(
                success=False,
                found=False,
                covered=False,
                requires_customer_verification=True,
                requires_product_selection=False,
                reason="CUSTOMER_NOT_VERIFIED",
                warranty=None,
                warranties=[],
            )

        reference_date = date.today()

        if arguments.product_sku is None:
            warranties = await self._repository.list_by_order_and_customer(
                order_number=arguments.order_number,
                customer_identification=customer_id,
            )

            if not warranties:
                clear_pending_warranty_action(
                    self._conversation_context,
                    PendingAction.CHECK_WARRANTY,
                )

                return WarrantyLookupResultDTO(
                    success=True,
                    found=False,
                    covered=False,
                    requires_customer_verification=False,
                    requires_product_selection=False,
                    reason="ORDER_OR_WARRANTY_NOT_FOUND",
                    warranty=None,
                    warranties=[],
                )

            if len(warranties) > 1:
                self._conversation_context.remember_warranty_lookup(
                    order_number=arguments.order_number,
                )

                return WarrantyLookupResultDTO(
                    success=True,
                    found=True,
                    covered=False,
                    requires_customer_verification=False,
                    requires_product_selection=True,
                    reason="PRODUCT_SELECTION_REQUIRED",
                    warranty=None,
                    warranties=[
                        warranty_to_summary_dto(
                            warranty,
                            reference_date,
                        )
                        for warranty in warranties
                    ],
                )

            warranty = warranties[0]

        else:
            warranty = await self._repository.get_by_order_product_and_customer(
                order_number=arguments.order_number,
                product_sku=arguments.product_sku,
                customer_identification=customer_id,
            )

            if warranty is None:
                clear_pending_warranty_action(
                    self._conversation_context,
                    PendingAction.CHECK_WARRANTY,
                )

                return WarrantyLookupResultDTO(
                    success=True,
                    found=False,
                    covered=False,
                    requires_customer_verification=False,
                    requires_product_selection=False,
                    reason="ORDER_OR_WARRANTY_NOT_FOUND",
                    warranty=None,
                    warranties=[],
                )

        summary = warranty_to_summary_dto(
            warranty=warranty,
            reference_date=reference_date,
        )

        failure_reason = get_coverage_failure_reason(
            warranty=warranty,
            reference_date=reference_date,
        )

        clear_pending_warranty_action(
            self._conversation_context,
            PendingAction.CHECK_WARRANTY,
        )

        if failure_reason is not None:
            return WarrantyLookupResultDTO(
                success=True,
                found=True,
                covered=False,
                requires_customer_verification=False,
                requires_product_selection=False,
                reason=failure_reason,
                warranty=summary,
                warranties=[],
            )

        self._conversation_context.remember_warranty(
            warranty_id=warranty.id,
            order_number=warranty.order_id,
            product_sku=warranty.product_sku,
        )

        return WarrantyLookupResultDTO(
            success=True,
            found=True,
            covered=True,
            requires_customer_verification=False,
            requires_product_selection=False,
            reason=None,
            warranty=summary,
            warranties=[],
        )


class RegisterWarrantyClaimTool(
    Tool[
        WarrantyClaimCreateInputDTO,
        WarrantyClaimCreateResultDTO,
    ]
):
    """
    Herramienta para registrar reclamos técnicos de garantía.

    Esta herramienta crea un ticket técnico únicamente cuando:

        - El cliente está verificado.
        - El pedido y el producto pertenecen al cliente.
        - Existe una garantía asociada al producto.
        - La garantía está vigente.
        - No existe ya un reclamo activo para esa garantía.

    También guarda en el contexto conversacional la garantía consultada, la
    descripción del problema y el número del ticket generado.
    """

    name = "register_warranty_claim"

    description = (
        "Registra un reclamo técnico para un producto con garantía vigente. "
        "Recibe número de pedido, SKU y descripción del problema. Comprueba "
        "nuevamente propiedad y cobertura antes de crear el ticket. Nunca "
        "recibe la identificación del cliente."
    )

    def __init__(
        self,
        repository: WarrantyRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta de registro de reclamos.

        Args:
            repository: Puerto usado para consultar garantías y crear reclamos.
            conversation_context: Contexto conversacional de la sesión actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[WarrantyClaimCreateInputDTO]:
        """
        Retorna el DTO de entrada esperado por la herramienta.

        Returns:
            Clase DTO usada para validar los argumentos de entrada.
        """

        return WarrantyClaimCreateInputDTO

    async def execute(
        self,
        arguments: WarrantyClaimCreateInputDTO,
    ) -> WarrantyClaimCreateResultDTO:
        """
        Registra un reclamo si la garantía continúa vigente.

        Si el cliente no está verificado, conserva el pedido, el SKU y la
        descripción del problema en el contexto conversacional para continuar el
        flujo después de la verificación.

        Args:
            arguments: Datos necesarios para crear el reclamo técnico.

        Returns:
            Resultado estructurado del intento de creación del reclamo.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.remember_warranty_lookup(
                order_number=arguments.order_number,
                product_sku=arguments.product_sku,
            )
            self._conversation_context.remember_warranty_issue(
                arguments.issue_description,
            )

            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="CUSTOMER_NOT_VERIFIED",
                ticket_number=None,
                claim=None,
                existing_claim=None,
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="CUSTOMER_NOT_VERIFIED",
                ticket_number=None,
                claim=None,
                existing_claim=None,
            )

        warranty = await self._repository.get_by_order_product_and_customer(
            order_number=arguments.order_number,
            product_sku=arguments.product_sku,
            customer_identification=customer_id,
        )

        if warranty is None:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.CREATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="ORDER_OR_WARRANTY_NOT_FOUND",
                ticket_number=None,
                claim=None,
                existing_claim=None,
            )

        if not warranty.is_valid_on(date.today()):
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.CREATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="WARRANTY_NOT_COVERED",
                ticket_number=None,
                claim=None,
                existing_claim=None,
            )

        existing_claim = await self._repository.get_open_claim_by_warranty_and_customer(
            warranty_id=warranty.id,
            customer_identification=customer_id,
        )

        if existing_claim is not None:
            self._conversation_context.remember_warranty(
                warranty_id=warranty.id,
                order_number=warranty.order_id,
                product_sku=warranty.product_sku,
            )
            self._conversation_context.remember_warranty_ticket(
                existing_claim.id,
            )

            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="CLAIM_ALREADY_EXISTS",
                ticket_number=None,
                claim=None,
                existing_claim=claim_to_dto(existing_claim),
            )

        claim = await self._repository.create_claim(
            claim_id=generate_claim_id(),
            warranty_id=warranty.id,
            customer_identification=customer_id,
            description=arguments.issue_description,
        )

        if claim is None:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.CREATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimCreateResultDTO(
                success=False,
                created=False,
                reason="ORDER_OR_WARRANTY_NOT_FOUND",
                ticket_number=None,
                claim=None,
                existing_claim=None,
            )

        self._conversation_context.remember_warranty(
            warranty_id=warranty.id,
            order_number=warranty.order_id,
            product_sku=warranty.product_sku,
        )
        self._conversation_context.remember_warranty_issue(
            arguments.issue_description,
        )
        self._conversation_context.remember_warranty_ticket(claim.id)

        claim_dto = claim_to_dto(claim)

        return WarrantyClaimCreateResultDTO(
            success=True,
            created=True,
            reason=None,
            ticket_number=claim.id,
            claim=claim_dto,
            existing_claim=None,
        )


class EscalateWarrantyClaimTool(
    Tool[
        WarrantyClaimEscalateInputDTO,
        WarrantyClaimEscalationResultDTO,
    ]
):
    """
    Herramienta para escalar un ticket de garantía a atención humana.

    Esta herramienta valida que:

        - El cliente esté verificado.
        - El ticket exista.
        - El ticket pertenezca al cliente.
        - El ticket no esté ya escalado.
        - El estado actual permita escalarlo.

    Solo los reclamos en estado `OPEN` o `IN_REVIEW` pueden escalarse. Los
    reclamos resueltos, rechazados o previamente escalados no se modifican.
    """

    name = "escalate_warranty_claim"

    description = (
        "Escala un ticket de garantía a atención humana. Recibe el número de "
        "ticket y el motivo concreto del escalamiento. Solo permite escalar "
        "tickets pertenecientes al cliente verificado y en estado OPEN o "
        "IN_REVIEW. Nunca recibe la identificación del cliente."
    )

    def __init__(
        self,
        repository: WarrantyRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta de escalamiento de reclamos.

        Args:
            repository: Puerto usado para consultar y escalar reclamos.
            conversation_context: Contexto conversacional de la sesión actual.
        """

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[WarrantyClaimEscalateInputDTO]:
        """
        Retorna el DTO de entrada esperado por la herramienta.

        Returns:
            Clase DTO usada para validar los argumentos de entrada.
        """

        return WarrantyClaimEscalateInputDTO

    async def execute(
        self,
        arguments: WarrantyClaimEscalateInputDTO,
    ) -> WarrantyClaimEscalationResultDTO:
        """
        Escala un ticket después de validar propietario y estado.

        Si el cliente no está verificado, conserva el número del ticket y el
        motivo del escalamiento en el contexto conversacional para continuar el
        flujo después de la verificación.

        Args:
            arguments: Datos necesarios para escalar el ticket.

        Returns:
            Resultado estructurado del intento de escalamiento.
        """

        if not self._conversation_context.is_customer_verified:
            self._conversation_context.remember_escalation(
                ticket_number=arguments.ticket_number,
                escalation_reason=arguments.escalation_reason,
            )

            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CUSTOMER_NOT_VERIFIED",
                claim=None,
            )

        customer_id = self._conversation_context.verified_customer_id

        if customer_id is None:
            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CUSTOMER_NOT_VERIFIED",
                claim=None,
            )

        existing_claim = await self._repository.get_claim_by_number_and_customer(
            ticket_number=arguments.ticket_number,
            customer_identification=customer_id,
        )

        if existing_claim is None:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.ESCALATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CLAIM_NOT_FOUND_OR_NOT_OWNED",
                claim=None,
            )

        if existing_claim.status is WarrantyClaimStatus.ESCALATED:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.ESCALATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CLAIM_ALREADY_ESCALATED",
                claim=None,
            )

        if existing_claim.status not in {
            WarrantyClaimStatus.OPEN,
            WarrantyClaimStatus.IN_REVIEW,
        }:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.ESCALATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CLAIM_NOT_ESCALATABLE",
                claim=None,
            )

        escalated_claim = await self._repository.escalate_claim(
            ticket_number=arguments.ticket_number,
            customer_identification=customer_id,
            escalation_reason=arguments.escalation_reason,
        )

        if escalated_claim is None:
            clear_pending_warranty_action(
                self._conversation_context,
                PendingAction.ESCALATE_WARRANTY_CLAIM,
            )

            return WarrantyClaimEscalationResultDTO(
                success=False,
                escalated=False,
                reason="CLAIM_NOT_ESCALATABLE",
                claim=None,
            )

        self._conversation_context.remember_escalation(
            ticket_number=escalated_claim.id,
            escalation_reason=arguments.escalation_reason,
        )
        self._conversation_context.clear_pending_action()

        return WarrantyClaimEscalationResultDTO(
            success=True,
            escalated=True,
            reason=None,
            claim=claim_to_dto(escalated_claim),
        )
