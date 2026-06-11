"""
Entidad de dominio para los pedidos de la tienda.

Este módulo define la representación principal de un pedido dentro del dominio
de la aplicación.

La entidad `Order` es independiente de frameworks, bases de datos, modelos ORM
o DTOs de entrada y salida. Su objetivo es expresar los datos relevantes del
negocio para los flujos de postventa, como consulta de estado, fecha estimada
de entrega y dirección asociada al pedido.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class OrderStatus(StrEnum):
    """
    Estados permitidos para un pedido.

    Este enum representa el ciclo de vida básico de un pedido dentro de la
    tienda. Permite evitar valores arbitrarios y facilita que servicios,
    herramientas y repositorios trabajen con estados controlados.

    Attributes:
        CONFIRMED: Pedido confirmado por el sistema.
        PREPARING: Pedido en preparación o alistamiento.
        SHIPPED: Pedido despachado desde la tienda o bodega.
        IN_TRANSIT: Pedido en tránsito hacia el cliente.
        DELIVERED: Pedido entregado correctamente.
        CANCELLED: Pedido cancelado.
    """

    CONFIRMED = "CONFIRMED"
    PREPARING = "PREPARING"
    SHIPPED = "SHIPPED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class Order:
    """
    Representa un pedido perteneciente a un cliente.

    Esta entidad contiene la información mínima necesaria para que el agente
    pueda responder consultas relacionadas con seguimiento de pedidos,
    estado actual, fecha estimada de entrega y dirección registrada.

    Al ser una entidad de dominio:

    - No depende de SQLAlchemy ni de modelos ORM.
    - No conoce cómo se almacena el pedido.
    - No genera respuestas conversacionales.
    - No ejecuta consultas ni actualizaciones.
    - Puede ser usada por servicios, repositorios y herramientas del agente.

    Attributes:
        id: Número único del pedido dentro del sistema.
        customer_id: Identificación del cliente propietario del pedido.
        status: Estado actual del pedido.
        estimated_delivery: Fecha estimada de entrega. Puede ser `None` si el
            pedido no tiene una fecha calculada o si el estado no aplica.
        address: Dirección de entrega asociada al pedido.

    Notes:
        `frozen=True` hace que la entidad sea inmutable después de creada.
        `slots=True` evita atributos dinámicos y reduce el uso de memoria.
    """

    id: str
    customer_id: str
    status: OrderStatus
    estimated_delivery: date | None
    address: str
