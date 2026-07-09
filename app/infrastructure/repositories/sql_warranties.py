"""
Repositorio PostgreSQL para garantías y reclamos técnicos.

Este módulo implementa el puerto `WarrantyRepository` usando SQLAlchemy y
PostgreSQL.

Su responsabilidad es consultar y persistir información relacionada con
garantías, reclamos técnicos y tickets de soporte, validando siempre que los
datos pertenezcan al cliente verificado en la sesión.

Esta validación evita consultar, exponer, crear o modificar información
asociada a otros clientes.

Responsabilidades principales:
    - Consultar garantías asociadas a un pedido y cliente.
    - Consultar una garantía específica por pedido, producto y cliente.
    - Consultar reclamos activos asociados a una garantía.
    - Registrar reclamos técnicos sobre garantías válidas.
    - Consultar tickets de soporte por número y cliente.
    - Escalar reclamos a atención humana.
    - Convertir modelos ORM en entidades de dominio.

"""

from sqlalchemy import and_, desc, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import RepositoryError
from app.application.ports.repositories import WarrantyRepository
from app.domain.entities import (
    Warranty,
    WarrantyClaim,
    WarrantyClaimStatus,
)
from app.infrastructure.db.models import (
    OrderItemModel,
    OrderModel,
    WarrantyClaimModel,
    WarrantyModel,
)

ACTIVE_CLAIM_STATUSES = frozenset(
    {
        WarrantyClaimStatus.OPEN.value,
        WarrantyClaimStatus.IN_REVIEW.value,
        WarrantyClaimStatus.ESCALATED.value,
    }
)
"""
Estados considerados activos para un reclamo de garantía.

Un reclamo activo es aquel que todavía requiere seguimiento por parte del
sistema o del equipo de soporte.
"""

ESCALATABLE_CLAIM_STATUSES = frozenset(
    {
        WarrantyClaimStatus.OPEN.value,
        WarrantyClaimStatus.IN_REVIEW.value,
    }
)
"""
Estados desde los cuales un reclamo puede escalarse a atención humana.

Los reclamos resueltos, rechazados o ya escalados no se vuelven a escalar desde
este repositorio.
"""


class SqlWarrantyRepository(WarrantyRepository):
    """
    Implementación PostgreSQL del repositorio de garantías.

    Esta clase implementa el puerto `WarrantyRepository` usando SQLAlchemy como
    mecanismo de acceso a datos.

    La sesión de base de datos se recibe mediante inyección de dependencias. El
    repositorio no crea ni cierra la sesión; únicamente ejecuta consultas,
    confirma escrituras y revierte transacciones cuando ocurre un error.

    La mayoría de consultas unen pedidos, líneas de pedido y garantías para
    comprobar que la garantía consultada pertenece realmente al cliente
    verificado.

    Attributes:
        _db: Sesión SQLAlchemy activa para la petición actual.
    """

    def __init__(
        self,
        db: AsyncSession,
    ) -> None:
        """
        Inicializa el repositorio.

        Args:
            db: Sesión SQLAlchemy asíncrona asociada a la petición actual.
        """

        self._db = db

    async def list_by_order_and_customer(
        self,
        order_number: str,
        customer_identification: str,
    ) -> list[Warranty]:
        """
        Lista las garantías de un pedido perteneciente a un cliente.

        La consulta une `warranties`, `orders` y `order_items` para validar que:

        - El pedido exista.
        - El pedido pertenezca al cliente indicado.
        - La garantía esté asociada a un producto incluido en ese pedido.

        La unión con `order_items` evita devolver garantías de productos que no
        formen parte real del pedido.

        Si el pedido no existe, pertenece a otro cliente o no tiene garantías,
        retorna una lista vacía. Esto evita revelar información de pedidos
        ajenos.

        Args:
            order_number: Número normalizado del pedido.
            customer_identification: Identificación del cliente verificado en la
                sesión.

        Returns:
            Lista de garantías asociadas al pedido y al cliente.

        Raises:
            RepositoryError: Si PostgreSQL no puede ejecutar la consulta.
        """

        statement = (
            select(WarrantyModel)
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                WarrantyModel.order_id == order_number,
                OrderModel.customer_id == customer_identification,
            )
            .order_by(
                WarrantyModel.product_sku,
                WarrantyModel.id,
            )
        )

        try:
            models = (await self._db.scalars(statement)).all()

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar las garantías del pedido") from exc

        return [self._warranty_to_entity(model) for model in models]

    async def get_by_order_product_and_customer(
        self,
        order_number: str,
        product_sku: str,
        customer_identification: str,
    ) -> Warranty | None:
        """
        Consulta una garantía validando pedido, producto y cliente.

        Esta operación se usa cuando el flujo necesita verificar la garantía de
        un producto específico dentro de un pedido concreto.

        Retorna `None` tanto si la garantía no existe como si el pedido
        pertenece a otro cliente. De esta manera no se revela información sobre
        compras o garantías ajenas.

        Args:
            order_number: Número normalizado del pedido.
            product_sku: SKU normalizado del producto.
            customer_identification: Identificación del cliente verificado en la
                sesión.

        Returns:
            Entidad `Warranty` si existe y pertenece al cliente; de lo
            contrario, None.

        Raises:
            RepositoryError: Si ocurre un error al consultar PostgreSQL.
        """

        statement = (
            select(WarrantyModel)
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                WarrantyModel.order_id == order_number,
                WarrantyModel.product_sku == product_sku,
                OrderModel.customer_id == customer_identification,
            )
        )

        try:
            model = await self._db.scalar(statement)

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar la garantía del producto") from exc

        if model is None:
            return None

        return self._warranty_to_entity(model)

    async def get_open_claim_by_warranty_and_customer(
        self,
        warranty_id: str,
        customer_identification: str,
    ) -> WarrantyClaim | None:
        """
        Consulta el reclamo activo más reciente de una garantía.

        Se consideran reclamos activos los que se encuentran en alguno de estos
        estados:

        - `OPEN`
        - `IN_REVIEW`
        - `ESCALATED`

        Además de validar el `customer_id` almacenado en el reclamo, la consulta
        comprueba que la garantía esté asociada a un pedido del mismo cliente.
        Esto protege el acceso incluso si la tabla de reclamos tuviera datos
        inconsistentes.

        El resultado se ordena por fecha de creación descendente y luego por id
        descendente para obtener el reclamo activo más reciente.

        Args:
            warranty_id: Identificador de la garantía.
            customer_identification: Identificación del cliente verificado en la
                sesión.

        Returns:
            Reclamo activo más reciente o None si no existe un reclamo válido
            para ese cliente.

        Raises:
            RepositoryError: Si ocurre un error al consultar PostgreSQL.
        """

        statement = (
            select(WarrantyClaimModel)
            .join(
                WarrantyModel,
                WarrantyClaimModel.warranty_id == WarrantyModel.id,
            )
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                WarrantyClaimModel.warranty_id == warranty_id,
                WarrantyClaimModel.customer_id == customer_identification,
                OrderModel.customer_id == customer_identification,
                WarrantyClaimModel.status.in_(ACTIVE_CLAIM_STATUSES),
            )
            .order_by(
                desc(WarrantyClaimModel.created_at),
                desc(WarrantyClaimModel.id),
            )
            .limit(1)
        )

        try:
            model = await self._db.scalar(statement)

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar los reclamos de la garantía") from exc

        if model is None:
            return None

        return self._claim_to_entity(model)

    async def create_claim(
        self,
        claim_id: str,
        warranty_id: str,
        customer_identification: str,
        description: str,
    ) -> WarrantyClaim | None:
        """
        Registra un reclamo y genera su ticket técnico.

        Antes de insertar el reclamo, el repositorio valida que la garantía
        exista y pertenezca al cliente indicado. Esta validación se realiza
        mediante la relación entre garantía, pedido y cliente.

        La vigencia de la garantía debe haberse comprobado previamente desde la
        herramienta o servicio de aplicación. Este repositorio valida propiedad,
        pero no decide si la garantía está vigente, vencida o si el caso debe
        escalarse por razones conversacionales.

        Args:
            claim_id: Identificador del reclamo. También funciona como número de
                ticket técnico.
            warranty_id: Identificador de la garantía asociada al reclamo.
            customer_identification: Identificación del cliente verificado en la
                sesión.
            description: Descripción del problema reportado por el cliente.

        Returns:
            Reclamo creado como entidad de dominio o None cuando la garantía no
            pertenece al cliente.

        Raises:
            RepositoryError: Si el identificador del ticket ya existe o si
            ocurre un error durante la escritura en PostgreSQL.
        """

        ownership_statement = (
            select(WarrantyModel.id)
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                WarrantyModel.id == warranty_id,
                OrderModel.customer_id == customer_identification,
            )
        )

        try:
            owned_warranty_id = await self._db.scalar(ownership_statement)

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible validar la garantía del cliente") from exc

        if owned_warranty_id is None:
            return None

        model = WarrantyClaimModel(
            id=claim_id,
            warranty_id=warranty_id,
            customer_id=customer_identification,
            description=description,
            status=WarrantyClaimStatus.OPEN.value,
            requires_human=False,
        )

        self._db.add(model)

        try:
            await self._db.commit()
            await self._db.refresh(model)

        except IntegrityError as exc:
            await self._db.rollback()

            raise RepositoryError(
                "No fue posible crear el ticket porque su identificador ya existe"
            ) from exc

        except SQLAlchemyError as exc:
            await self._db.rollback()

            raise RepositoryError("No fue posible registrar el reclamo de garantía") from exc

        return self._claim_to_entity(model)

    async def get_claim_by_number_and_customer(
        self,
        ticket_number: str,
        customer_identification: str,
    ) -> WarrantyClaim | None:
        """
        Consulta un ticket técnico validando que pertenezca al cliente.

        La consulta une reclamos, garantías, pedidos y líneas de pedido para
        verificar que el ticket solicitado esté asociado a una garantía de un
        producto comprado por el cliente indicado.

        Retornar `None` cuando el ticket no pertenece al cliente evita revelar
        la existencia de tickets ajenos.

        Args:
            ticket_number: Identificador del reclamo y número de ticket.
            customer_identification: Identificación del cliente verificado en la
                sesión.

        Returns:
            Reclamo encontrado como entidad de dominio o None si no existe o no
            pertenece al cliente.

        Raises:
            RepositoryError: Si ocurre un error al consultar PostgreSQL.
        """

        statement = (
            select(WarrantyClaimModel)
            .join(
                WarrantyModel,
                WarrantyClaimModel.warranty_id == WarrantyModel.id,
            )
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                WarrantyClaimModel.id == ticket_number,
                WarrantyClaimModel.customer_id == customer_identification,
                OrderModel.customer_id == customer_identification,
            )
        )

        try:
            model = await self._db.scalar(statement)

        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar el ticket de garantía") from exc

        if model is None:
            return None

        return self._claim_to_entity(model)

    async def escalate_claim(
        self,
        ticket_number: str,
        customer_identification: str,
        escalation_reason: str,
    ) -> WarrantyClaim | None:
        """
        Escala un reclamo a atención humana.

        Esta operación actualiza el estado del reclamo a `ESCALATED` y marca
        `requires_human` como True.

        La propiedad del ticket y el estado actual se validan dentro de la misma
        sentencia `UPDATE`. Esto permite:

        - Impedir que se escalen tickets de otros clientes.
        - Evitar condiciones de carrera si otro proceso cambia el estado del
          reclamo al mismo tiempo.
        - Garantizar que solo se escalen reclamos en estados permitidos.

        Solo pueden escalarse reclamos en estado `OPEN` o `IN_REVIEW`.

        Args:
            ticket_number: Número del ticket técnico.
            customer_identification: Identificación del cliente verificado en la
                sesión.
            escalation_reason: Motivo concreto por el cual el reclamo requiere
                atención humana.

        Returns:
            Reclamo escalado como entidad de dominio o None cuando el ticket no
            existe, pertenece a otro cliente o su estado no permite
            escalamiento.

        Raises:
            RepositoryError: Si ocurre un error al actualizar PostgreSQL.
        """

        owned_warranties = (
            select(WarrantyModel.id)
            .join(
                OrderModel,
                WarrantyModel.order_id == OrderModel.id,
            )
            .join(
                OrderItemModel,
                and_(
                    OrderItemModel.order_id == WarrantyModel.order_id,
                    OrderItemModel.product_sku == WarrantyModel.product_sku,
                ),
            )
            .where(
                OrderModel.customer_id == customer_identification,
            )
        )

        statement = (
            update(WarrantyClaimModel)
            .where(
                WarrantyClaimModel.id == ticket_number,
                WarrantyClaimModel.customer_id == customer_identification,
                WarrantyClaimModel.warranty_id.in_(owned_warranties),
                WarrantyClaimModel.status.in_(ESCALATABLE_CLAIM_STATUSES),
            )
            .values(
                status=WarrantyClaimStatus.ESCALATED.value,
                requires_human=True,
                escalation_reason=escalation_reason,
            )
            .returning(WarrantyClaimModel)
        )

        try:
            model = (await self._db.scalars(statement)).one_or_none()
            await self._db.commit()

        except SQLAlchemyError as exc:
            await self._db.rollback()

            raise RepositoryError("No fue posible escalar el reclamo de garantía") from exc

        if model is None:
            return None

        return self._claim_to_entity(model)

    @staticmethod
    def _warranty_to_entity(
        model: WarrantyModel,
    ) -> Warranty:
        """
        Convierte un modelo ORM de garantía en una entidad de dominio.

        Esta conversión mantiene separada la capa de infraestructura de la capa
        de dominio. El resto de la aplicación debe trabajar con `Warranty`, no
        con `WarrantyModel`.

        Args:
            model: Modelo ORM obtenido desde PostgreSQL.

        Returns:
            Entidad de dominio `Warranty`.
        """

        return Warranty(
            id=model.id,
            product_sku=model.product_sku,
            order_id=model.order_id,
            active=model.active,
            starts_on=model.starts_on,
            expires_on=model.expires_on,
        )

    @staticmethod
    def _claim_to_entity(
        model: WarrantyClaimModel,
    ) -> WarrantyClaim:
        """
        Convierte un modelo ORM de reclamo en una entidad de dominio.

        También valida que el estado almacenado en PostgreSQL exista dentro del
        enum `WarrantyClaimStatus`. Si la base de datos contiene un valor no
        reconocido, se lanza `RepositoryError` para evitar propagar un estado
        inválido a la capa de dominio.

        Args:
            model: Modelo ORM obtenido desde PostgreSQL.

        Returns:
            Entidad de dominio `WarrantyClaim`.

        Raises:
            RepositoryError: Si PostgreSQL contiene un estado no reconocido.
        """

        try:
            status = WarrantyClaimStatus(model.status)

        except ValueError as exc:
            raise RepositoryError("El reclamo contiene un estado no reconocido") from exc

        return WarrantyClaim(
            id=model.id,
            warranty_id=model.warranty_id,
            customer_id=model.customer_id,
            description=model.description,
            status=status,
            requires_human=model.requires_human,
            escalation_reason=model.escalation_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
