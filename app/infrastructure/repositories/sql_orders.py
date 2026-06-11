"""Repositorio PostgreSQL para consultas y actualización de pedidos."""

from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.exceptions import RepositoryError
from app.application.ports.repositories import OrderRepository
from app.domain.entities import Order
from app.infrastructure.db.models import OrderModel

UPDATABLE_ORDER_STATUSES = frozenset({"CONFIRMED", "PREPARING"})


class SqlOrderRepository(OrderRepository):
    """Consulta pedidos garantizando el filtro por cliente."""

    def __init__(self, db: Session) -> None:
        self._db = db

    async def list_by_customer(
        self,
        customer_identification: str,
    ) -> list[Order]:
        statement = (
            select(OrderModel)
            .where(OrderModel.customer_id == customer_identification)
            .order_by(desc(OrderModel.created_at))
        )

        try:
            models = self._db.scalars(statement).all()
        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar los pedidos del cliente") from exc

        return [self._to_entity(model) for model in models]

    async def get_by_number(
        self,
        order_number: str,
    ) -> Order | None:
        try:
            model = self._db.get(
                OrderModel,
                order_number,
            )
        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar el pedido") from exc

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_number_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> Order | None:
        statement = select(OrderModel).where(
            OrderModel.id == order_number,
            OrderModel.customer_id == customer_identification,
        )

        try:
            model = self._db.scalar(statement)
        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar el pedido del cliente") from exc

        if model is None:
            return None

        return self._to_entity(model)

    async def update_delivery_address(
        self,
        order_number: str,
        customer_identification: str,
        new_address: str,
    ) -> Order | None:
        statement = select(OrderModel).where(
            OrderModel.id == order_number,
            OrderModel.customer_id == customer_identification,
        )

        try:
            model = self._db.scalar(statement)

            if model is None or model.status not in UPDATABLE_ORDER_STATUSES:
                return None

            model.address = new_address
            self._db.commit()
            self._db.refresh(model)
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise RepositoryError("No fue posible actualizar la dirección del pedido") from exc

        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: OrderModel) -> Order:
        return Order(
            id=model.id,
            customer_id=model.customer_id,
            status=model.status,
            estimated_delivery=model.estimated_delivery,
            address=model.address,
        )
