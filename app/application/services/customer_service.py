"""Casos de uso de identificación y registro de clientes."""

from dataclasses import dataclass

from app.application.ports.repositories import CustomerRepository
from app.domain.entities import Customer
from app.domain.value_objects.contact import Email, Phone
from app.domain.value_objects.identity import FullName, Identification


@dataclass(frozen=True, slots=True)
class CustomerRegistrationOutcome:
    """Resultado interno de un intento de registro."""

    customer: Customer | None
    conflict_field: str | None = None

    @property
    def created(self) -> bool:
        return self.customer is not None


class CustomerService:
    """Coordina validación, consulta y registro de clientes."""

    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    async def find_by_identification(self, identification: str) -> Customer | None:
        normalized = Identification(identification.strip()).value
        return await self._repository.get_by_identification(normalized)

    async def register(
        self,
        identification: str,
        full_name: str,
        phone: str,
        email: str,
    ) -> CustomerRegistrationOutcome:
        normalized_identification = Identification(identification.strip()).value
        normalized_name = " ".join(full_name.split())
        FullName(normalized_name)
        normalized_phone = Phone(phone.strip()).value
        normalized_email = Email(email.strip().lower()).value

        if await self._repository.get_by_identification(normalized_identification):
            return CustomerRegistrationOutcome(customer=None, conflict_field="identification")

        if await self._repository.get_by_email(normalized_email):
            return CustomerRegistrationOutcome(customer=None, conflict_field="email")

        customer = Customer(
            identification=normalized_identification,
            full_name=normalized_name,
            phone=normalized_phone,
            email=normalized_email,
            kind="NEW",
        )
        created_customer = await self._repository.create(customer)

        if created_customer is not None:
            return CustomerRegistrationOutcome(customer=created_customer)

        if await self._repository.get_by_identification(normalized_identification):
            return CustomerRegistrationOutcome(customer=None, conflict_field="identification")

        return CustomerRegistrationOutcome(customer=None, conflict_field="email")
