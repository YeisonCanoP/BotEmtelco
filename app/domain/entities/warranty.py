from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Warranty:
    id: str
    product_sku: str
    order_id: str
    active: bool
    expires_on: date
