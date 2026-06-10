"""Adaptador para generar respuestas mediante OpenAI."""

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.application.dtos import (
    ChatMessageDTO,
    LLMRequestDTO,
    LLMResponseDTO,
    MessageRole,
)
from app.infrastructure.config import Settings, get_settings


class OpenAIProvider:
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
        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": request.instructions,
            },
            *[self._to_openai_message(message) for message in request.messages],
        ]

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = response.choices[0].message.content

        if not content:
            raise ValueError("OpenAI no devolvió contenido en la respuesta")

        return LLMResponseDTO(content=content)

    @staticmethod
    def _to_openai_message(
        message: ChatMessageDTO,
    ) -> ChatCompletionMessageParam:
        if message.role is MessageRole.USER:
            return {
                "role": "user",
                "content": message.content,
            }

        return {
            "role": "assistant",
            "content": message.content,
        }
