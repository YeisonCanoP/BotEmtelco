from app.application.tools.base import Tool
from app.application.tools.catalog_tools import (
    CompareProductsTool,
    SearchCatalogTool,
)
from app.application.tools.customer_tools import (
    FindCustomerTool,
    RegisterCustomerTool,
    customer_to_result_dto,
)
from app.application.tools.handoff_tools import (
    RequestHumanSupportTool,
    human_handoff_to_dto,
)
from app.application.tools.knowledge_tools import SearchKnowledgeBaseTool
from app.application.tools.order_tools import (
    GetCustomerOrderTool,
    ListCustomerOrdersTool,
    UpdateOrderAddressTool,
    order_to_detail_dto,
    order_to_summary_dto,
)
from app.application.tools.registry import ToolRegistry
from app.application.tools.warranty_tools import (
    CheckWarrantyTool,
    EscalateWarrantyClaimTool,
    RegisterWarrantyClaimTool,
    claim_to_dto,
    warranty_to_summary_dto,
)

__all__ = [
    "CheckWarrantyTool",
    "CompareProductsTool",
    "EscalateWarrantyClaimTool",
    "FindCustomerTool",
    "GetCustomerOrderTool",
    "ListCustomerOrdersTool",
    "RegisterCustomerTool",
    "RegisterWarrantyClaimTool",
    "RequestHumanSupportTool",
    "SearchCatalogTool",
    "SearchKnowledgeBaseTool",
    "Tool",
    "ToolRegistry",
    "UpdateOrderAddressTool",
    "claim_to_dto",
    "customer_to_result_dto",
    "human_handoff_to_dto",
    "order_to_detail_dto",
    "order_to_summary_dto",
    "warranty_to_summary_dto",
]
