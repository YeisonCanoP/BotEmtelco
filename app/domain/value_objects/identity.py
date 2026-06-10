from dataclasses import dataclass

from app.domain.exceptions import DomainError


@dataclass(frozen=True, slots=True)
class Identification:
    value: str

    def __post_init__(self) -> None:
        if not self.value.isdigit() or not 4 <= len(self.value) <= 11:
            raise DomainError("Identification must contain 4 to 11 digits")


@dataclass(frozen=True, slots=True)
class FullName:
    value: str

    def __post_init__(self) -> None:
        if not 1 <= len(self.value.strip()) <= 100:
            raise DomainError("Full name must contain 1 to 100 characters")
