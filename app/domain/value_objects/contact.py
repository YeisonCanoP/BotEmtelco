from dataclasses import dataclass

from app.domain.exceptions import DomainError


@dataclass(frozen=True, slots=True)
class Phone:
    value: str

    def __post_init__(self) -> None:
        if len(self.value) != 10 or not self.value.isdigit() or self.value[0] not in {"3", "6"}:
            raise DomainError("Phone must contain 10 digits and start with 3 or 6")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        local, separator, domain = self.value.partition("@")
        if not separator or not local or "." not in domain:
            raise DomainError("Invalid email address")
