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
from app.application.tools.order_tools import (
    GetCustomerOrderTool,
    ListCustomerOrdersTool,
    UpdateOrderAddressTool,
    order_to_detail_dto,
    order_to_summary_dto,
)
from app.application.tools.registry import ToolRegistry

__all__ = [
    "CompareProductsTool",
    "FindCustomerTool",
    "GetCustomerOrderTool",
    "ListCustomerOrdersTool",
    "RegisterCustomerTool",
    "SearchCatalogTool",
    "Tool",
    "ToolRegistry",
    "UpdateOrderAddressTool",
    "customer_to_result_dto",
    "order_to_detail_dto",
    "order_to_summary_dto",
]
