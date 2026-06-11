"""Herramientas disponibles para el agente conversacional."""

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
from app.application.tools.registry import ToolRegistry

__all__ = [
    "CompareProductsTool",
    "FindCustomerTool",
    "RegisterCustomerTool",
    "SearchCatalogTool",
    "Tool",
    "ToolRegistry",
    "customer_to_result_dto",
]
