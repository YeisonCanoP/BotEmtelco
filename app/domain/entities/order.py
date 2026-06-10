from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Order:
    id: str
    customer_id: str
    status: str
    estimated_delivery: date | None
    address: str
