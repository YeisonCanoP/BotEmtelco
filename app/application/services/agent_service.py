"""
Servicio principal del agente conversacional.

Este módulo contiene la lógica de aplicación encargada de procesar mensajes
entrantes del usuario, recuperar o crear la sesión conversacional, invocar el
proveedor de lenguaje y persistir el estado actualizado de la conversación.
"""

import logging

from app.application.dtos import (
    AgentRequestDTO,
    AgentResponseDTO,
    ChatMessageDTO,
    ConversationDTO,
    LLMRequestDTO,
    MessageRole,
)
from app.application.exceptions import LLMServiceError
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.session_store import SessionStore
from app.application.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class AgentService:
    """
    Servicio de aplicación para procesar conversaciones del agente.

    Coordina el flujo principal del agente conversacional:
    recupera la conversación existente, agrega el mensaje del usuario,
    solicita una respuesta al proveedor LLM, guarda la respuesta generada
    y persiste el estado actualizado de la sesión.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        session_store: SessionStore,
    ) -> None:
        """
        Inicializa el servicio del agente.

        Args:
            llm_provider: Proveedor encargado de generar respuestas mediante un LLM.
            session_store: Almacenamiento usado para recuperar y guardar sesiones.
        """
        self._llm_provider = llm_provider
        self._session_store = session_store

    async def handle(
        self,
        request: AgentRequestDTO,
    ) -> AgentResponseDTO:
        """
        Procesa un mensaje entrante y retorna la respuesta del agente.

        Si la sesión no existe, crea una nueva conversación. Luego agrega el
        mensaje del usuario al historial, invoca el proveedor LLM con las
        instrucciones del sistema y el contexto conversacional, almacena la
        respuesta generada y guarda la conversación actualizada.

        Args:
            request: Solicitud del usuario con el identificador de sesión y el
                mensaje a procesar.

        Returns:
            AgentResponseDTO: Respuesta normalizada del agente para el usuario.
        """
        conversation = await self._session_store.get(request.session_id)

        if conversation is None:
            conversation = ConversationDTO(
                session_id=request.session_id,
            )

            logger.info(
                "Conversación creada session_id=%s",
                request.session_id,
            )

        conversation.messages.append(
            ChatMessageDTO(
                role=MessageRole.USER,
                content=request.message,
            )
        )

        llm_response = await self._llm_provider.complete(
            LLMRequestDTO(
                instructions=SYSTEM_PROMPT,
                messages=conversation.messages,
            )
        )

        if llm_response.content is None:
            raise LLMServiceError(
                "El modelo solicitó herramientas, pero el servicio aún no puede ejecutarlas"
            )

        reply = llm_response.content

        conversation.messages.append(
            ChatMessageDTO(
                role=MessageRole.ASSISTANT,
                content=reply,
            )
        )

        await self._session_store.save(conversation)

        logger.info(
            "Conversación procesada session_id=%s message_count=%s",
            request.session_id,
            len(conversation.messages),
        )

        return AgentResponseDTO(
            session_id=request.session_id,
            reply=reply,
        )
