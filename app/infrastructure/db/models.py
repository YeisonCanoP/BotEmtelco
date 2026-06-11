"""
Modelos ORM utilizados para persistir información de la tienda.

Este módulo define las representaciones de base de datos para las entidades
principales del negocio que deben almacenarse en PostgreSQL.

Los modelos declarados aquí pertenecen a la capa de infraestructura. Su
responsabilidad es describir tablas, columnas, tipos de datos, restricciones e
información necesaria para que SQLAlchemy pueda mapear registros de la base de
datos a objetos Python.

- Las entidades de dominio viven en `app.domain.entities`.
- Los DTOs de entrada y salida viven en `app.application.dtos`.
- Los repositorios concretos usan estos modelos para leer y escribir datos.
- Los servicios y herramientas trabajan contra puertos, no contra estos modelos
    directamente.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ProductModel(Base):
    """
    Representación ORM de la tabla `products`.

    Esta tabla almacena los productos disponibles en el catálogo de la tienda.
    El agente utiliza esta información, a través de un repositorio, para buscar
    productos, consultar precios, comparar alternativas y recomendar opciones
    según la necesidad del cliente.

    Attributes:
        sku: Código único del producto. Funciona como clave primaria.
        name: Nombre comercial del producto.
        category: Categoría general del producto, por ejemplo celulares,
            computadores, televisores o accesorios.
        description: Descripción textual del producto.
        price: Precio actual del producto con dos decimales.
        stock: Cantidad disponible en inventario.
        specs: Especificaciones técnicas almacenadas como JSONB. Permite guardar
            atributos variables según el tipo de producto, por ejemplo memoria,
            procesador, tamaño de pantalla, almacenamiento o conectividad.

    Notes:
        `specs` usa JSONB porque las características técnicas pueden cambiar
        entre categorías de productos. Un computador, un celular y un televisor
        no necesariamente comparten los mismos campos.
    """

    __tablename__ = "products"

    sku: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    stock: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    specs: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )


class CustomerModel(Base):
    """
    Representación ORM de la tabla `customers`.

    Esta tabla almacena los clientes registrados en la tienda. El agente utiliza
    esta información, mediante el repositorio de clientes, para validar clientes
    frecuentes, evitar registros duplicados y asociar solicitudes de pedidos o
    garantías a una persona identificada.

    Attributes:
        identification: Número de identificación del cliente. Funciona como
            clave primaria.
        full_name: Nombre completo del cliente.
        phone: Número telefónico del cliente.
        email: Correo electrónico del cliente. Debe ser único en la tabla.
        kind: Clasificación comercial del cliente, por ejemplo `NEW` o
            `FREQUENT`.
        created_at: Fecha y hora en la que el cliente fue registrado.

    Notes:
        Las validaciones estrictas de identificación, teléfono, nombre y correo
        deben ejecutarse antes de persistir el modelo, por ejemplo desde DTOs,
        servicios de aplicación o herramientas del agente.

        Este modelo solo expresa restricciones de persistencia como longitud,
        nulabilidad, clave primaria y unicidad.
    """

    __tablename__ = "customers"

    identification: Mapped[str] = mapped_column(
        String(11),
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    kind: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="NEW",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OrderModel(Base):
    """Representación ORM de la tabla `orders`."""

    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )

    customer_id: Mapped[str] = mapped_column(
        String(11),
        ForeignKey("customers.identification"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    estimated_delivery: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    address: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
