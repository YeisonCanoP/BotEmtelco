"""Modelos ORM del sistema de retail."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
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


class CustomerModel(Base):
    """Modelo de persistencia de clientes."""

    __tablename__ = "customers"

    identification: Mapped[str] = mapped_column(String(11), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str] = mapped_column(String(10), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class OrderModel(Base):
    """Modelo de persistencia de pedidos."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(11),
        ForeignKey("customers.identification"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    estimated_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    address: Mapped[str] = mapped_column(String(250), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
