"""
Modelo ORM de productos.

Este módulo define la representación de la tabla `products`, usada para
almacenar el catálogo de productos disponibles en el sistema de retail.
"""

from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ProductModel(Base):
    """
    Modelo de base de datos para productos.

    Representa los productos electrónicos disponibles en el catálogo,
    incluyendo información comercial, inventario y características técnicas.

    Attributes:
        sku: Código único del producto.
        name: Nombre comercial del producto.
        category: Categoría a la que pertenece el producto.
        description: Descripción general del producto.
        price: Precio del producto.
        stock: Cantidad disponible en inventario.
        specs: Especificaciones técnicas del producto en formato JSON.
    """

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(String(30), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock: Mapped[int] = mapped_column(nullable=False, default=0)
    specs: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
