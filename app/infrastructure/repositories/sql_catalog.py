"""
Repositorio PostgreSQL para consultas del catálogo.

Este módulo implementa el acceso a datos del catálogo de productos usando
SQLAlchemy y PostgreSQL. Permite buscar productos por texto, categoría,
precio máximo y disponibilidad en inventario.
"""

from decimal import Decimal

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from app.application.ports.repositories import CatalogRepository
from app.domain.entities import Product
from app.infrastructure.db.models import ProductModel


class SqlCatalogRepository(CatalogRepository):
    """
    Repositorio SQL para consultar productos del catálogo.

    Encapsula las consultas sobre la tabla `products` y transforma los modelos
    ORM de infraestructura en entidades de dominio.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    async def search(
        self,
        query: str,
        category: str | None = None,
        max_price: Decimal | None = None,
        in_stock_only: bool = True,
        limit: int = 10,
    ) -> list[Product]:
        """
        Busca productos en el catálogo aplicando filtros opcionales.

        La búsqueda puede realizarse sobre el nombre, categoría, descripción
        y especificaciones técnicas del producto. También permite filtrar por
        categoría exacta, precio máximo y disponibilidad en inventario.

        Args:
            query: Texto usado para buscar coincidencias en el catálogo.
            category: Categoría opcional para limitar la búsqueda.
            max_price: Precio máximo permitido para los productos retornados.
            in_stock_only: Indica si solo se deben incluir productos con stock.
            limit: Cantidad máxima de resultados a retornar.

        Returns:
            list[Product]: Lista de productos encontrados como entidades de dominio.
        """
        normalized_query = query.strip()
        statement = select(ProductModel)

        if normalized_query:
            pattern = f"%{normalized_query}%"

            statement = statement.where(
                or_(
                    ProductModel.name.ilike(pattern),
                    ProductModel.category.ilike(pattern),
                    ProductModel.description.ilike(pattern),
                    cast(ProductModel.specs, String).ilike(pattern),
                )
            )

        if category and (normalized_category := category.strip()):
            statement = statement.where(ProductModel.category == normalized_category.upper())

        if max_price is not None:
            statement = statement.where(ProductModel.price <= max_price)

        if in_stock_only:
            statement = statement.where(ProductModel.stock > 0)

        statement = statement.order_by(ProductModel.price).limit(max(1, min(limit, 50)))

        models = self._db.scalars(statement).all()

        return [self._to_entity(model) for model in models]

    async def get_by_skus(
        self,
        skus: list[str],
    ) -> list[Product]:
        """
        Consulta productos específicos por sus códigos SKU.

        Los SKU son normalizados a mayúsculas. Los valores vacíos y duplicados
        son descartados. Los productos encontrados se retornan respetando el
        orden solicitado.

        Args:
            skus: Códigos SKU que se desean consultar.

        Returns:
            list[Product]: Productos encontrados en el orden solicitado.
        """
        normalized_skus = list(dict.fromkeys(sku.strip().upper() for sku in skus if sku.strip()))

        if not normalized_skus:
            return []

        statement = select(ProductModel).where(ProductModel.sku.in_(normalized_skus))

        models = self._db.scalars(statement).all()

        models_by_sku = {model.sku: model for model in models}

        return [
            self._to_entity(models_by_sku[sku]) for sku in normalized_skus if sku in models_by_sku
        ]

    @staticmethod
    def _to_entity(model: ProductModel) -> Product:
        """
        Convierte un modelo ORM en una entidad de dominio.

        Args:
            model: Producto recuperado mediante SQLAlchemy.

        Returns:
            Product: Entidad de producto independiente de la base de datos.
        """
        return Product(
            sku=model.sku,
            name=model.name,
            category=model.category,
            description=model.description,
            price=model.price,
            stock=model.stock,
            specs=dict(model.specs),
        )
