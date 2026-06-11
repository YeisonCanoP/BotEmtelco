"""Repositorio PostgreSQL de clientes."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.ports.repositories import CustomerRepository
from app.domain.entities import Customer
from app.infrastructure.db.models import CustomerModel


class SqlCustomerRepository(CustomerRepository):
    """Consulta y registra clientes usando SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    async def get_by_identification(self, identification: str) -> Customer | None:
        model = self._db.get(CustomerModel, identification.strip())
        return self._to_entity(model) if model is not None else None

    async def get_by_email(self, email: str) -> Customer | None:
        statement = select(CustomerModel).where(CustomerModel.email == email.strip().lower())
        model = self._db.scalar(statement)
        return self._to_entity(model) if model is not None else None

    async def create(self, customer: Customer) -> Customer | None:
        model = CustomerModel(
            identification=customer.identification,
            full_name=customer.full_name,
            phone=customer.phone,
            email=customer.email,
            kind=customer.kind,
        )
        self._db.add(model)

        try:
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            return None

        self._db.refresh(model)
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: CustomerModel) -> Customer:
        return Customer(
            identification=model.identification,
            full_name=model.full_name,
            phone=model.phone,
            email=model.email,
            kind=model.kind,
        )
