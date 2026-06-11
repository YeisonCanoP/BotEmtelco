"""
Modelos ORM utilizados para persistir información de la tienda.

Este módulo define las representaciones de base de datos para las entidades
principales del negocio que deben almacenarse en PostgreSQL.


Separación de responsabilidades:
    - Las entidades de dominio viven en `app.domain.entities`.
    - Los DTOs de entrada y salida viven en `app.application.dtos`.
    - Los repositorios concretos usan estos modelos para leer y escribir datos.
    - Los servicios y herramientas trabajan contra puertos, no contra estos
      modelos directamente.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class ProductModel(Base):
    """
    Representación ORM de la tabla `products`.

    Almacena los productos disponibles en el catálogo de la tienda. Esta
    información es consultada por el agente, mediante repositorios concretos,
    para responder solicitudes de venta consultiva, búsqueda de productos,
    comparación de alternativas, validación de precios, disponibilidad en stock
    y recomendaciones según la necesidad del cliente.

    Attributes:
        sku: Código único del producto. Funciona como clave primaria.
        name: Nombre comercial del producto.
        category: Categoría general del producto, por ejemplo celulares,
            computadores, televisores o accesorios.
        description: Descripción textual del producto.
        price: Precio actual del producto, almacenado con dos decimales.
        stock: Cantidad disponible en inventario.
        specs: Especificaciones técnicas almacenadas como JSONB.

    Notes:
        `specs` usa JSONB porque las características técnicas pueden variar
        según la categoría del producto. Por ejemplo, un computador puede tener
        procesador, memoria RAM y tarjeta gráfica, mientras que un televisor
        puede tener resolución, tipo de panel y tamaño de pantalla.

        Este modelo solo representa la estructura persistida. La lógica de
        recomendación, comparación o filtrado debe implementarse en servicios,
        repositorios o herramientas del agente.
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

    Almacena los clientes registrados en la tienda. El agente usa esta
    información, a través de repositorios, para validar clientes frecuentes,
    registrar clientes nuevos, evitar duplicados y asociar pedidos o solicitudes
    de garantía a una persona identificada.

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
        Las validaciones estrictas de identificación, nombre, teléfono y correo
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
    """
    Representación ORM de la tabla `orders`.

    Almacena los pedidos realizados por los clientes. Esta tabla permite
    consultar el estado de una compra, revisar la fecha estimada de entrega,
    actualizar la dirección de envío y relacionar productos comprados con
    garantías posteriores.

    Attributes:
        id: Identificador único del pedido.
        customer_id: Identificación del cliente asociado al pedido.
        status: Estado actual del pedido.
        estimated_delivery: Fecha estimada de entrega. Puede ser nula cuando
            todavía no existe una fecha calculada o confirmada.
        address: Dirección de entrega del pedido.
        created_at: Fecha y hora de creación del pedido.
        updated_at: Fecha y hora de la última actualización del pedido.

    Notes:
        `customer_id` referencia `customers.identification`, lo que garantiza
        que cada pedido pertenezca a un cliente registrado.

        Los cambios de estado del pedido deben controlarse desde la capa de
        aplicación o dominio. El modelo ORM no debe decidir transiciones como
        enviado, entregado, cancelado o en preparación.
    """

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


class OrderItemModel(Base):
    """
    Representación ORM de la tabla `order_items`.

    Relaciona productos con pedidos. Cada registro representa una línea de
    compra dentro de un pedido específico, indicando qué producto fue adquirido,
    cuántas unidades se compraron y cuál fue el precio unitario registrado en el
    momento de la compra.

    Esta tabla también es necesaria para los flujos de garantía, porque permite
    comprobar que un producto realmente pertenece a un pedido antes de consultar
    o registrar una solicitud de soporte.

    Attributes:
        id: Identificador interno de la línea del pedido.
        order_id: Identificador del pedido al que pertenece la línea.
        product_sku: SKU del producto comprado.
        quantity: Cantidad comprada del producto.
        unit_price: Precio unitario registrado al realizar la compra.
        created_at: Fecha y hora de creación de la línea del pedido.

    Notes:
        La restricción única `order_items_order_product_unique` evita que el
        mismo producto se registre más de una vez dentro del mismo pedido. Si el
        cliente compra varias unidades del mismo producto, la cantidad debe
        representarse con el campo `quantity`.
    """

    __tablename__ = "order_items"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_sku",
            name="order_items_order_product_unique",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    order_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("orders.id"),
        nullable=False,
    )

    product_sku: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("products.sku"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WarrantyModel(Base):
    """
    Representación ORM de la tabla `warranties`.

    Almacena la garantía asociada a un producto comprado dentro de un pedido.
    Cada garantía queda vinculada tanto al pedido como al SKU del producto, lo
    que permite validar si un cliente tiene cobertura vigente para un artículo
    específico.

    La vigencia administrativa se expresa mediante `active`, mientras que la
    vigencia temporal se determina con `starts_on` y `expires_on`. La decisión
    final sobre si una garantía está vigente debe realizarse desde la entidad de
    dominio correspondiente.

    Attributes:
        id: Identificador único de la garantía.
        product_sku: SKU del producto cubierto por la garantía.
        order_id: Pedido mediante el cual se compró el producto.
        active: Indica si la garantía está habilitada administrativamente.
        starts_on: Fecha de inicio de la cobertura.
        expires_on: Fecha final de la cobertura.
        created_at: Fecha y hora de creación del registro.

    Notes:
        La restricción única `warranties_order_product_unique` evita registrar
        más de una garantía para el mismo producto dentro del mismo pedido.

        Este modelo no decide si la garantía está vencida o si aplica para un
        caso específico. Esa regla debe vivir en la entidad de dominio
        `Warranty` o en el servicio de aplicación que coordine el flujo de
        soporte.
    """

    __tablename__ = "warranties"

    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_sku",
            name="warranties_order_product_unique",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(30),
        primary_key=True,
    )

    product_sku: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("products.sku"),
        nullable=False,
    )

    order_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("orders.id"),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    starts_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    expires_on: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class KnowledgeChunkModel(Base):
    """
    Representación ORM de la tabla `kb_chunks`.

    Almacena fragmentos de conocimiento usados por el agente para responder
    preguntas frecuentes, políticas de la tienda, guías de solución de
    problemas, instrucciones de soporte o información complementaria que no
    necesariamente pertenece al catálogo transaccional.

    Cada fragmento puede incluir un embedding generado por un modelo de
    lenguaje. Ese vector permite realizar búsqueda semántica con pgvector y
    recuperar contenido relevante para enriquecer las respuestas del agente.

    Attributes:
        id: Identificador interno del fragmento.
        source: Documento, archivo o fuente de la cual proviene el fragmento.
        title: Título descriptivo del fragmento.
        content: Contenido textual utilizado para responder al usuario.
        chunk_metadata: Metadatos adicionales almacenados físicamente en la
            columna `metadata`.
        embedding: Vector semántico de 1536 dimensiones. Puede ser nulo cuando
            el fragmento aún no ha sido vectorizado.
        created_at: Fecha y hora de creación del fragmento.

    Notes:
        El atributo Python se llama `chunk_metadata` porque `metadata` es un
        nombre reservado dentro de los modelos declarativos de SQLAlchemy. Sin
        embargo, en PostgreSQL la columna real se guarda con el nombre
        `metadata`.

        La dimensión `Vector(1536)` debe coincidir con el modelo de embeddings
        utilizado por la aplicación. Si se cambia el modelo de embeddings, esta
        dimensión también debe revisarse.
    """

    __tablename__ = "kb_chunks"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536),
        nullable=True,
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WarrantyClaimModel(Base):
    """
    Representación ORM de la tabla `warranty_claims`.

    Un reclamo funciona también como ticket técnico. Su identificador se
    entrega al cliente como número de ticket.

    Attributes:
        id: Identificador del reclamo y número de ticket.
        warranty_id: Garantía asociada.
        customer_id: Cliente propietario del reclamo.
        description: Problema reportado por el cliente.
        status: Estado actual del reclamo.
        requires_human: Indica si necesita atención humana.
        escalation_reason: Motivo por el cual el caso fue escalado.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última actualización.
    """

    __tablename__ = "warranty_claims"

    id: Mapped[str] = mapped_column(
        String(40),
        primary_key=True,
    )

    warranty_id: Mapped[str] = mapped_column(
        String(30),
        ForeignKey("warranties.id"),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(11),
        ForeignKey("customers.identification"),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="OPEN",
    )

    requires_human: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    escalation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
