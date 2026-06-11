"""Repositorio PostgreSQL para consultas de pedidos."""

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.application.ports.repositories import OrderRepository
from app.domain.entities import Order
from app.infrastructure.db.models import OrderModel


class SqlOrderRepository(OrderRepository):
    """Consulta pedidos garantizando el filtro por cliente."""

    def __init__(self, db: Session) -> None:
        self._db = db

    async def list_by_customer(self, customer_id: str) -> list[Order]:
        statement = (
            select(OrderModel)
            .where(OrderModel.customer_id == customer_id)
            .order_by(desc(OrderModel.created_at))
        )
        models = self._db.scalars(statement).all()

        return [
            Order(
                id=model.id,
                customer_id=model.customer_id,
                status=model.status,
                estimated_delivery=model.estimated_delivery,
                address=model.address,
            )
            for model in models
        ]
