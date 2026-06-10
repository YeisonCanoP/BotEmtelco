from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    category: str
    price: Decimal
    stock: int
    specs: dict[str, Any] = field(default_factory=dict)
