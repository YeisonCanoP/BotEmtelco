"""DTOs utilizados por el flujo conversacional."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """Roles admitidos dentro de una conversación."""

    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageDTO(BaseModel):
    """Representa un mensaje de la conversación."""

    role: MessageRole
    content: str = Field(min_length=1, max_length=20_000)


class ConversationDTO(BaseModel):
    """Estado de una sesión conversacional."""

    session_id: UUID
    messages: list[ChatMessageDTO] = Field(default_factory=list)


class AgentRequestDTO(BaseModel):
    """Entrada del caso de uso del agente."""

    session_id: UUID
    message: str = Field(min_length=1, max_length=4_000)


class AgentResponseDTO(BaseModel):
    """Resultado producido por el agente."""

    session_id: UUID
    reply: str


class LLMRequestDTO(BaseModel):
    """Solicitud independiente del proveedor de IA."""

    instructions: str
    messages: list[ChatMessageDTO]


class LLMResponseDTO(BaseModel):
    """Respuesta normalizada de un proveedor de IA."""

    content: str
