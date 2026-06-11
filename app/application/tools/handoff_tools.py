"""
Herramienta para transferir una conversación a atención humana.

La herramienta crea una solicitud general independiente de garantías. Puede
usarse con sesiones anónimas y nunca recibe la identificación del cliente como
argumento del modelo.
"""

from uuid import uuid4

from app.application.dtos import (
    HumanHandoffDTO,
    HumanHandoffInputDTO,
    HumanHandoffResultDTO,
)
from app.application.ports.repositories import HumanHandoffRepository
from app.application.services.conversation_context import ConversationContext
from app.application.tools.base import Tool
from app.domain.entities import HumanHandoff, HumanHandoffReason


def human_handoff_to_dto(
    handoff: HumanHandoff,
) -> HumanHandoffDTO:
    """
    Convierte una solicitud de dominio en una salida segura para el agente.

    La identificación del cliente y el identificador interno de la sesión no se
    incluyen porque no son necesarios para confirmar el escalamiento.
    """

    return HumanHandoffDTO(
        id=handoff.id,
        reason=handoff.reason,
        summary=handoff.summary,
        status=handoff.status,
    )


def generate_handoff_id() -> str:
    """Genera un identificador único para una solicitud de atención humana."""

    return f"HND-{uuid4().hex.upper()}"


class RequestHumanSupportTool(
    Tool[
        HumanHandoffInputDTO,
        HumanHandoffResultDTO,
    ]
):
    """
    Herramienta para solicitar atención de un asesor humano.

    Solo debe utilizarse cuando el usuario la solicita explícitamente o cuando,
    después de una pregunta de aclaración, el agente continúa sin entender la
    intención. No debe invocarse por errores técnicos ni información faltante
    que pueda solicitarse normalmente.
    """

    name = "request_human_support"

    description = (
        "Solicita atención de un asesor humano para la conversación actual. "
        "Úsala inmediatamente si el usuario pide hablar con una persona. "
        "También puedes usarla con reason INTENT_NOT_UNDERSTOOD, pero únicamente "
        "después de haber formulado una pregunta concreta de aclaración y recibir "
        "otra respuesta que siga sin permitir identificar la intención. "
        "No la uses por errores técnicos, resultados vacíos, datos faltantes, "
        "solicitudes fuera de alcance ni reglas de negocio. "
        "No recibe session_id ni identificación del cliente."
    )

    def __init__(
        self,
        repository: HumanHandoffRepository,
        conversation_context: ConversationContext,
    ) -> None:
        """Inicializa la herramienta con repositorio y contexto conversacional."""

        self._repository = repository
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[HumanHandoffInputDTO]:
        """Retorna el DTO usado para validar los argumentos."""

        return HumanHandoffInputDTO

    async def execute(
        self,
        arguments: HumanHandoffInputDTO,
    ) -> HumanHandoffResultDTO:
        """
        Crea o reutiliza la solicitud activa de la sesión.

        La sesión se obtiene del contexto interno. El cliente solo se asocia si
        ya estaba verificado; nunca se solicita identificación para escalar.
        """

        conversation = self._conversation_context.conversation

        existing = await self._repository.get_active_by_session(
            conversation.session_id,
        )

        if existing is not None:
            return HumanHandoffResultDTO(
                success=True,
                escalated=False,
                already_pending=True,
                handoff=human_handoff_to_dto(existing),
            )

        customer_id = (
            self._conversation_context.verified_customer_id
            if self._conversation_context.is_customer_verified
            else None
        )

        handoff, created = await self._repository.create(
            handoff_id=generate_handoff_id(),
            session_id=conversation.session_id,
            customer_identification=customer_id,
            reason=HumanHandoffReason(arguments.reason),
            summary=arguments.summary,
        )

        return HumanHandoffResultDTO(
            success=True,
            escalated=created,
            already_pending=not created,
            handoff=human_handoff_to_dto(handoff),
        )
