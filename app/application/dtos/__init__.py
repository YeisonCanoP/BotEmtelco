"""
DTO compartidos por la capa de aplicación.

Este módulo centraliza las exportaciones para evitar que servicios,
herramientas e interfaces dependan de las rutas internas de cada archivo.
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
    CustomerFlowStatus,
    CustomerRegistrationDraftDTO,
    MessageRole,
    PendingAction,
)
from app.application.dtos.customer import (
    CustomerLookupInputDTO,
    CustomerLookupResultDTO,
    CustomerRegistrationInputDTO,
    CustomerRegistrationResultDTO,
    CustomerResultDTO,
)
from app.application.dtos.llm import (
    LLMRequestDTO,
    LLMResponseDTO,
    ToolCallDTO,
    ToolDefinitionDTO,
    ToolResultDTO,
)
from app.application.dtos.order import (
    CustomerOrdersInputDTO,
    CustomerOrdersResultDTO,
    OrderAddressFailureReason,
    OrderAddressUpdateResultDTO,
    OrderDetailDTO,
    OrderLookupInputDTO,
    OrderLookupResultDTO,
    OrderSummaryDTO,
    UpdateOrderAddressInputDTO,
)

__all__ = [
    "AgentRequestDTO",
    "AgentResponseDTO",
    "CatalogSearchInputDTO",
    "CatalogSearchResultDTO",
    "ChatMessageDTO",
    "CompareProductsInputDTO",
    "ConversationDTO",
    "CustomerFlowStatus",
    "CustomerLookupInputDTO",
    "CustomerLookupResultDTO",
    "CustomerOrdersInputDTO",
    "CustomerOrdersResultDTO",
    "OrderAddressFailureReason",
    "OrderAddressUpdateResultDTO",
    "OrderDetailDTO",
    "OrderLookupInputDTO",
    "OrderLookupResultDTO",
    "OrderSummaryDTO",
    "UpdateOrderAddressInputDTO",
    "CustomerRegistrationDraftDTO",
    "CustomerRegistrationInputDTO",
    "CustomerRegistrationResultDTO",
    "CustomerResultDTO",
    "LLMRequestDTO",
    "LLMResponseDTO",
    "MessageRole",
    "PendingAction",
    "ProductComparisonResultDTO",
    "ProductResultDTO",
    "ToolCallDTO",
    "ToolDefinitionDTO",
    "ToolResultDTO",
]
