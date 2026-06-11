"""
Servicio principal del agente conversacional.

Este módulo coordina el flujo de conversación del agente. Recupera o crea la
sesión del usuario, agrega el mensaje entrante al historial, invoca el proveedor
LLM, ejecuta herramientas cuando el modelo las solicita y persiste la respuesta
final de la conversación.

El servicio mantiene separadas las responsabilidades de aplicación:
- El historial se administra mediante `SessionStore`.
- La generación de respuestas se delega a `LLMProvider`.
- Las herramientas se consultan y ejecutan mediante `ToolRegistry`.
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
    ToolError,
)
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.session_store import SessionStore
from app.application.prompts.system_prompt import SYSTEM_PROMPT
from app.application.tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentService:
    """
    Orquestador principal del agente conversacional.

    Gestiona el ciclo completo de una interacción:
    recibe un mensaje del usuario, conserva el contexto de la sesión, permite
    que el modelo solicite herramientas, ejecuta esas herramientas y finalmente
    retorna una respuesta natural para el usuario.

    Attributes:
        _llm_provider: Proveedor usado para comunicarse con el modelo de lenguaje.
        _session_store: Almacenamiento de sesiones conversacionales.
        _tool_registry: Registro de herramientas disponibles para el agente.
        _max_tool_rounds: Límite de rondas consecutivas de uso de herramientas.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        session_store: SessionStore,
        tool_registry: ToolRegistry,
        max_tool_rounds: int,
    ) -> None:
        """
        Inicializa el servicio del agente.

        Args:
            llm_provider: Proveedor de lenguaje usado para generar respuestas.
            session_store: Almacenamiento usado para recuperar y guardar sesiones.
            tool_registry: Registro de herramientas que el agente puede ejecutar.
            max_tool_rounds: Número máximo de rondas de herramientas permitidas.

        Raises:
            ValueError: Si `max_tool_rounds` es menor que uno.
        """
        if max_tool_rounds < 1:
            raise ValueError("max_tool_rounds debe ser mayor o igual a 1")

        self._llm_provider = llm_provider
        self._session_store = session_store
        self._tool_registry = tool_registry
        self._max_tool_rounds = max_tool_rounds

    async def handle(
        self,
        request: AgentRequestDTO,
    ) -> AgentResponseDTO:
        """
        Procesa un mensaje entrante y retorna la respuesta final del agente.

        El flujo agrega el mensaje del usuario al historial, envía la solicitud
        al proveedor LLM con las herramientas disponibles y ejecuta las llamadas
        de herramientas que el modelo solicite. Cuando el modelo produce una
        respuesta final, esta se guarda en la conversación y se retorna al
        cliente.

        Args:
            request: Solicitud normalizada con identificador de sesión y mensaje
                del usuario.

        Returns:
            AgentResponseDTO: Respuesta final del agente asociada a la sesión.

        Raises:
            LLMServiceError: Si el modelo excede el límite de rondas de
                herramientas, solicita herramientas sin `response_id` o no
                produce una respuesta final.
        """
        conversation = await self._get_conversation(request)

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
            "Conversation processed session_id=%s message_count=%s tool_rounds=%s",
            request.session_id,
            len(conversation.messages),
            tool_rounds,
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
            request: Solicitud actual del usuario con el identificador de sesión.

        Returns:
            ConversationDTO: Conversación existente o una nueva conversación
            vacía asociada al `session_id`.
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

        Las ejecuciones se realizan de forma secuencial para evitar conflictos
        con repositorios o sesiones de base de datos que no estén preparados
        para ejecución paralela.

        Args:
            tool_calls: Llamadas de herramientas generadas por el proveedor LLM.

        Returns:
            list[ToolResultDTO]: Resultados de herramientas relacionados con su
            respectivo `call_id`.
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
        una salida estructurada para que el modelo pueda corregir argumentos,
        intentar otra acción o explicar al usuario que no pudo completar la
        operación.

        Args:
            name: Nombre de la herramienta solicitada por el modelo.
            arguments: Argumentos generados por el modelo para la herramienta.

        Returns:
            dict[str, Any]: Resultado exitoso de la herramienta o error
            controlado en formato serializable.
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

        except ToolError as exc:
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
