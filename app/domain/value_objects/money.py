from dataclasses import dataclass
from decimal import Decimal

from app.domain.exceptions import DomainError


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "COP"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise DomainError("Money amount cannot be negative")
