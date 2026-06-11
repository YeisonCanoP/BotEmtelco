"""
Adaptador para generar respuestas mediante OpenAI.

Este módulo implementa el proveedor concreto encargado de comunicarse con
OpenAI usando el contrato de aplicación definido para generación de respuestas
del agente conversacional.
"""

import logging

from openai import AsyncOpenAI, OpenAIError
from openai.types.responses import (
    EasyInputMessageParam,
    ResponseInputParam,
    ResponseTextConfigParam,
)
from openai.types.shared_params import Reasoning

from app.application.dtos import (
    ChatMessageDTO,
    LLMRequestDTO,
    LLMResponseDTO,
    MessageRole,
)
from app.application.exceptions import LLMServiceError
from app.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """
    Proveedor de respuestas basado en OpenAI.

    Esta clase adapta las solicitudes internas de la aplicación al formato
    esperado por la API de OpenAI y transforma la respuesta obtenida en un DTO
    normalizado para el resto del sistema.
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()

        if not self._settings.openai_api_key:
            raise ValueError("La variable OPENAI_API_KEY no está configurada")

        self._client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
        )

        self._model = self._settings.openai_model

    async def complete(
        self,
        request: LLMRequestDTO,
    ) -> LLMResponseDTO:
        """
        Genera una respuesta del agente mediante OpenAI.

        Convierte el historial conversacional al formato requerido por OpenAI,
        envía la solicitud al modelo configurado y retorna una respuesta
        normalizada con el contenido generado y la información de uso de tokens.

        Args:
            request: Solicitud normalizada con instrucciones del sistema e
                historial de mensajes de la conversación.

        Returns:
            LLMResponseDTO: Respuesta generada por OpenAI, incluyendo contenido,
            identificador de respuesta, modelo usado y métricas de tokens.

        Raises:
            LLMServiceError: Si OpenAI retorna un error o si la respuesta
                generada está vacía.
        """
        input_messages: ResponseInputParam = [
            self._to_openai_message(message) for message in request.messages
        ]
        reasoning: Reasoning = {
            "effort": self._settings.openai_reasoning_effort,
        }
        text: ResponseTextConfigParam = {
            "verbosity": self._settings.openai_verbosity,
        }

        logger.info(
            "Sending OpenAI request model=%s reasoning_effort=%s verbosity=%s",
            self._settings.openai_model,
            self._settings.openai_reasoning_effort,
            self._settings.openai_verbosity,
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=request.instructions,
                input=input_messages,
                reasoning=reasoning,
                text=text,
                max_output_tokens=self._settings.openai_max_output_tokens,
                temperature=self._settings.openai_temperature,
                top_p=self._settings.openai_top_p,
                store=False,
                stream=False,
            )
        except OpenAIError as exc:
            logger.exception(
                "OpenAI request failed model=%s",
                self._settings.openai_model,
            )
            raise LLMServiceError("No fue posible obtener respuesta del modelo") from exc

        content = response.output_text.strip()

        if not content:
            raise LLMServiceError("OpenAI devolvió una respuesta vacía")

        usage = response.usage
        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0

        reasoning_tokens = 0

        if usage and usage.output_tokens_details:
            reasoning_tokens = usage.output_tokens_details.reasoning_tokens or 0

        logger.info(
            "OpenAI request completed response_id=%s "
            "input_tokens=%s output_tokens=%s "
            "reasoning_tokens=%s",
            response.id,
            input_tokens,
            output_tokens,
            reasoning_tokens,
        )

        return LLMResponseDTO(
            content=content,
            response_id=response.id,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
        )

    @staticmethod
    def _to_openai_message(
        message: ChatMessageDTO,
    ) -> EasyInputMessageParam:
        """
        Convierte un mensaje interno al formato aceptado por OpenAI.

        Args:
            message: Mensaje de la conversación representado como DTO interno.

        Returns:
            EasyInputMessageParam: Mensaje adaptado al formato de entrada de
            OpenAI.
        """
        if message.role is MessageRole.USER:
            return {
                "role": "user",
                "content": message.content,
            }

        return {
            "role": "assistant",
            "content": message.content,
        }
