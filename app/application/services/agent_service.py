"""
Servicio principal del agente conversacional.

Este módulo coordina el flujo completo de una conversación con el agente.
Recupera o crea la sesión del usuario, agrega el mensaje entrante al historial,
invoca el proveedor LLM, ejecuta herramientas cuando el modelo las solicita y
persiste el estado final de la conversación.

El servicio mantiene separadas las responsabilidades de aplicación:

- El historial y el estado de sesión se administran mediante `SessionStore`.
- La generación de respuestas se delega a `LLMProvider`.
- Las herramientas disponibles se consultan y ejecutan mediante `ToolRegistry`.
- El estado estructurado de la conversación se comparte con herramientas usando
  `ConversationContext`.

Además del historial de mensajes, la conversación puede conservar información
como cliente verificado, borrador de registro, acción pendiente y referencias
necesarias para continuar flujos de pedidos, garantías o ventas.
"""

import logging
from typing import Any

from app.application.dtos import (
    AgentRequestDTO,
    AgentResponseDTO,
    ChatMessageDTO,
    ConversationDTO,
    LLMRequestDTO,
    MessageRole,
    ToolCallDTO,
    ToolResultDTO,
)
from app.application.exceptions import (
    LLMServiceError,
    RepositoryError,
    ToolError,
)
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.session_store import SessionStore
from app.application.prompts.system_prompt import SYSTEM_PROMPT
from app.application.services.conversation_context import (
    ConversationContext,
)
from app.application.tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentService:
    """
    Orquestador principal del agente conversacional.

    Gestiona el ciclo completo de una interacción:

    - Recupera o crea la conversación asociada a la sesión.
    - Enlaza la conversación al contexto compartido.
    - Agrega el mensaje del usuario al historial.
    - Solicita una respuesta al proveedor LLM.
    - Ejecuta herramientas cuando el modelo las solicita.
    - Entrega los resultados de herramientas nuevamente al modelo.
    - Guarda la respuesta final del asistente.
    - Persiste la conversación actualizada.

    El servicio no implementa lógica específica de catálogo, pedidos, clientes o
    garantías. Esa lógica vive en herramientas y servicios especializados.

    Attributes:
        _llm_provider: Proveedor usado para comunicarse con el modelo de
            lenguaje.
        _session_store: Almacenamiento persistente de conversaciones.
        _tool_registry: Registro de herramientas disponibles para el agente.
        _conversation_context: Contexto mutable compartido con las herramientas.
        _max_tool_rounds: Límite de rondas consecutivas de uso de herramientas.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        session_store: SessionStore,
        tool_registry: ToolRegistry,
        conversation_context: ConversationContext,
        max_tool_rounds: int,
    ) -> None:
        """
        Inicializa el servicio del agente.

        Args:
            llm_provider: Proveedor de lenguaje usado para generar respuestas.
            session_store: Almacenamiento usado para recuperar y guardar
                conversaciones.
            tool_registry: Registro de herramientas que el agente puede
                ejecutar.
            conversation_context: Contexto compartido con las herramientas
                durante una petición.
            max_tool_rounds: Número máximo de rondas de herramientas
                permitidas antes de detener el flujo.

        Raises:
            ValueError: Si `max_tool_rounds` es menor que uno.
        """

        if max_tool_rounds < 1:
            raise ValueError("max_tool_rounds debe ser mayor o igual a 1")

        self._llm_provider = llm_provider
        self._session_store = session_store
        self._tool_registry = tool_registry
        self._conversation_context = conversation_context
        self._max_tool_rounds = max_tool_rounds

    async def handle(
        self,
        request: AgentRequestDTO,
    ) -> AgentResponseDTO:
        """
        Procesa un mensaje entrante y retorna la respuesta final del agente.

        El flujo agrega el mensaje del usuario al historial, envía la solicitud
        al proveedor LLM con las herramientas disponibles y ejecuta las llamadas
        de herramientas que el modelo solicite.

        Antes de invocar herramientas, la conversación se enlaza al
        `ConversationContext`. Esto permite que herramientas como validación de
        clientes, registro, pedidos o garantías modifiquen el mismo objeto de
        conversación que luego será persistido.

        Args:
            request: Solicitud normalizada con identificador de sesión y mensaje
                del usuario.

        Returns:
            Respuesta final del agente asociada a la sesión.

        Raises:
            LLMServiceError: Si el modelo excede el límite de rondas de
                herramientas, solicita herramientas sin `response_id` o no
                produce una respuesta final.
        """

        conversation = await self._get_conversation(request)

        self._conversation_context.bind(conversation)

        conversation.messages.append(
            ChatMessageDTO(
                role=MessageRole.USER,
                content=request.message,
            )
        )

        tool_definitions = self._tool_registry.definitions()

        llm_response = await self._llm_provider.complete(
            LLMRequestDTO(
                instructions=SYSTEM_PROMPT,
                messages=conversation.messages,
                tools=tool_definitions,
            )
        )

        tool_rounds = 0

        while llm_response.tool_calls:
            if tool_rounds >= self._max_tool_rounds:
                raise LLMServiceError("El agente excedió el límite de rondas de herramientas")

            if llm_response.response_id is None:
                raise LLMServiceError("El modelo solicitó herramientas sin response_id")

            tool_results = await self._execute_tool_calls(llm_response.tool_calls)

            tool_rounds += 1

            logger.info(
                "Tool round completed session_id=%s round=%s calls=%s",
                request.session_id,
                tool_rounds,
                len(tool_results),
            )

            llm_response = await self._llm_provider.complete(
                LLMRequestDTO(
                    instructions=SYSTEM_PROMPT,
                    messages=conversation.messages,
                    tools=tool_definitions,
                    tool_results=tool_results,
                    previous_response_id=llm_response.response_id,
                )
            )

        if llm_response.content is None:
            raise LLMServiceError("El modelo no produjo una respuesta final")

        reply = llm_response.content

        conversation.messages.append(
            ChatMessageDTO(
                role=MessageRole.ASSISTANT,
                content=reply,
            )
        )

        await self._session_store.save(conversation)

        logger.info(
            "Conversation processed session_id=%s "
            "message_count=%s tool_rounds=%s customer_status=%s",
            request.session_id,
            len(conversation.messages),
            tool_rounds,
            conversation.customer_status,
        )

        return AgentResponseDTO(
            session_id=request.session_id,
            reply=reply,
        )

    async def _get_conversation(
        self,
        request: AgentRequestDTO,
    ) -> ConversationDTO:
        """
        Recupera la conversación asociada a la sesión o crea una nueva.

        Args:
            request: Solicitud actual del usuario con el identificador de
                sesión.

        Returns:
            Conversación existente recuperada desde el almacenamiento de sesión
            o una nueva conversación vacía asociada al `session_id`.
        """

        conversation = await self._session_store.get(request.session_id)

        if conversation is not None:
            return conversation

        logger.info(
            "Conversation created session_id=%s",
            request.session_id,
        )

        return ConversationDTO(
            session_id=request.session_id,
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[ToolCallDTO],
    ) -> list[ToolResultDTO]:
        """
        Ejecuta las herramientas solicitadas por el modelo.

        Las herramientas se ejecutan de forma secuencial para evitar conflictos
        con sesiones de base de datos, contexto conversacional mutable o
        repositorios que no estén preparados para ejecución paralela.

        Args:
            tool_calls: Llamadas de herramientas generadas por el proveedor LLM.

        Returns:
            Lista de resultados de herramientas asociados a su respectivo
            `call_id`.
        """

        results: list[ToolResultDTO] = []

        for tool_call in tool_calls:
            output = await self._execute_tool_call(
                name=tool_call.name,
                arguments=tool_call.arguments,
            )

            results.append(
                ToolResultDTO(
                    call_id=tool_call.call_id,
                    output=output,
                )
            )

        return results

    async def _execute_tool_call(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Ejecuta una herramienta registrada y captura errores controlados.

        Si la herramienta falla por un error esperado, el error se convierte en
        una salida estructurada. Esto permite que el modelo corrija argumentos,
        intente otra acción o explique al usuario que no pudo completar la
        operación.

        Args:
            name: Nombre de la herramienta solicitada por el modelo.
            arguments: Argumentos generados por el modelo para la herramienta.

        Returns:
            Resultado exitoso de la herramienta o error controlado en formato
            serializable.
        """

        logger.info(
            "Executing tool name=%s",
            name,
        )

        try:
            return await self._tool_registry.execute(
                name=name,
                arguments=arguments,
            )

        except (ToolError, RepositoryError) as exc:
            logger.warning(
                "Tool execution failed name=%s error=%s",
                name,
                type(exc).__name__,
            )

            return {
                "success": False,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
