"""
Repositorio PostgreSQL para consultas y actualización de pedidos.

Este módulo contiene la implementación concreta del puerto `OrderRepository`
usando SQLAlchemy y PostgreSQL.

Todas las consultas que acceden a un pedido específico validan que el pedido
pertenezca al cliente indicado. Esto evita exponer información de pedidos
asociados a otros clientes.

La actualización de dirección valida el propietario y el estado del pedido
dentro de la misma sentencia SQL. De esta forma se evita una condición de
carrera en la que el pedido cambie de estado entre una consulta previa y la
actualización.
"""

from sqlalchemy import desc, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import RepositoryError
from app.application.ports.repositories import OrderRepository
from app.domain.entities import Order, OrderStatus
from app.infrastructure.db.models import OrderModel

UPDATABLE_ORDER_STATUSES = frozenset(
    {
        OrderStatus.CONFIRMED.value,
        OrderStatus.PREPARING.value,
    }
)


class SqlOrderRepository(OrderRepository):
    """
    Implementación PostgreSQL del repositorio de pedidos.

    Esta clase adapta el contrato `OrderRepository` a una base de datos
    relacional usando SQLAlchemy.

    Todas las operaciones que consultan o actualizan un pedido específico
    reciben la identificación del cliente. Esto permite verificar propiedad y
    evita entregar información de pedidos ajenos.

    Attributes:
        _db: Sesión SQLAlchemy activa usada para consultar y actualizar pedidos.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:

        self._db = db

    async def list_by_customer(
        self,
        customer_identification: str,
    ) -> list[Order]:
        """
        Lista los pedidos pertenecientes a un cliente.

        Este métod se usa cuando el usuario solicita ver sus pedidos y ya
        existe un cliente verificado en la conversación.

        Los resultados se ordenan desde el pedido más reciente hasta el más
        antiguo usando `created_at` y, como criterio secundario, el identificador
        del pedido.

        Args:
            customer_identification: Identificación del cliente verificado en la
                conversación.

        Returns:
            Lista de pedidos pertenecientes al cliente.

        Raises:
            RepositoryError: Si ocurre un error al consultar la base de datos.
        """

        statement = (
            select(OrderModel)
            .where(OrderModel.customer_id == customer_identification)
            .order_by(
                desc(OrderModel.created_at),
                desc(OrderModel.id),
            )
        )

        try:
            models = (await self._db.scalars(statement)).all()

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar los pedidos del cliente") from exc

        return [self._to_entity(model) for model in models]

    async def get_by_number_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> Order | None:
        """
        Consulta un pedido validando simultáneamente su propietario.

        Este métodoa consulta. Si el pedido no existe o pertenece a otro
        cliente, retorna `None`.

        Retornar `None` en ambos casos evita revelar la existencia de pedidos
        ajenos.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Identificación del cliente verificado en la
                conversación.

        Returns:
            Entidad `Order` si el pedido existe y pertenece al cliente. Retorna
            `None` si no existe o no pertenece al cliente indicado.

        Raises:
            RepositoryError: Si ocurre un error al consultar la base de datos.
        """

        statement = select(OrderModel).where(
            OrderModel.id == order_number,
            OrderModel.customer_id == customer_identification,
        )

        try:
            model = await self._db.scalar(statement)

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
        """
        Actualiza la dirección de entrega de un pedido modificable.

        La comprobación del número de pedido, propietario y estado se realiza
        dentro de una única sentencia `UPDATE`.

        Esto garantiza que la dirección solo se actualice si:

        - El pedido existe.
        - El pedido pertenece al cliente verificado.
        - El pedido está en un estado que permite cambios de dirección.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Identificación del cliente verificado en la
                conversación.
            new_address: Nueva dirección de entrega validada y normalizada.

        Returns:
            Pedido actualizado como entidad de dominio. Retorna `None` cuando el
            pedido no existe, pertenece a otro cliente o su estado no permite
            modificar la dirección.

        Raises:
            RepositoryError: Si ocurre un error al actualizar la base de datos.
        """

        statement = (
            update(OrderModel)
            .where(
                OrderModel.id == order_number,
                OrderModel.customer_id == customer_identification,
                OrderModel.status.in_(UPDATABLE_ORDER_STATUSES),
            )
            .values(
                address=new_address,
            )
            .returning(OrderModel)
        )

        try:
            model = (await self._db.scalars(statement)).one_or_none()

            await self._db.commit()

        except SQLAlchemyError as exc:
            await self._db.rollback()

            raise RepositoryError("No fue posible actualizar la dirección del pedido") from exc

        if model is None:
            return None

        return self._to_entity(model)

    @staticmethod
    def _to_entity(
        model: OrderModel,
    ) -> Order:
        """
        Convierte un modelo ORM en una entidad de dominio.

        Esta conversión evita que las capas superiores trabajen directamente con
        objetos SQLAlchemy. El repositorio encapsula los modelos de
        infraestructura y retorna entidades independientes de la base de datos.

        También valida que el estado almacenado en PostgreSQL corresponda a uno
        de los estados reconocidos por el dominio.

        Args:
            model: Pedido recuperado o actualizado mediante SQLAlchemy.

        Returns:
            Entidad `Order` independiente de la infraestructura.

        Raises:
            RepositoryError: Si el estado almacenado en la base de datos no
                corresponde a ningún valor de `OrderStatus`.
        """

        try:
            status = OrderStatus(model.status)

        except ValueError as exc:
            raise RepositoryError("El pedido contiene un estado no reconocido") from exc

        return Order(
            id=model.id,
            customer_id=model.customer_id,
            status=status,
            estimated_delivery=model.estimated_delivery,
            address=model.address,
        )
