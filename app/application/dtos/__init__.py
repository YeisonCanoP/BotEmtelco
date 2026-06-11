"""
DTOs compartidos por la capa de aplicación.
"""

from app.application.dtos.catalog import (
    CatalogSearchInputDTO,
    CatalogSearchResultDTO,
    CompareProductsInputDTO,
    ProductComparisonResultDTO,
    ProductResultDTO,
)
from app.application.dtos.chat import (
    AgentRequestDTO,
    AgentResponseDTO,
    ChatMessageDTO,
    ConversationDTO,
    MessageRole,
)
from app.application.dtos.llm import (
    LLMRequestDTO,
    LLMResponseDTO,
    ToolCallDTO,
    ToolDefinitionDTO,
    ToolResultDTO,
)

__all__ = [
    "AgentRequestDTO",
    "AgentResponseDTO",
    "CatalogSearchInputDTO",
    "CatalogSearchResultDTO",
    "ChatMessageDTO",
    "CompareProductsInputDTO",
    "ConversationDTO",
    "LLMRequestDTO",
    "LLMResponseDTO",
    "MessageRole",
    "ProductComparisonResultDTO",
    "ProductResultDTO",
    "ToolCallDTO",
    "ToolDefinitionDTO",
    "ToolResultDTO",
]
