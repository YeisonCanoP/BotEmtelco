"""
Entidad de dominio que representa a un cliente.

Este módulo define el modelo central de cliente utilizado por la capa de
dominio de la aplicación. La entidad representa a una persona registrada en la
tienda y contiene únicamente los datos propios del negocio.

La clase no depende de frameworks, bases de datos, validadores HTTP ni modelos
de persistencia. Esto permite que el dominio permanezca desacoplado de detalles
como FastAPI, SQLAlchemy, PostgreSQL, Redis o Pydantic.
"""

from dataclasses import dataclass
from typing import Literal, TypeGuard

CustomerKind = Literal["NEW", "FREQUENT"]


def is_customer_kind(value: str) -> TypeGuard[CustomerKind]:
    """Indica si un valor corresponde a una clasificación de cliente válida."""

    return value in ("NEW", "FREQUENT")


@dataclass(frozen=True, slots=True)
class Customer:
    """
    Representa un cliente registrado en la tienda.

    Esta entidad forma parte del dominio y describe la información mínima
    necesaria para identificar y contactar a un cliente dentro de los flujos de
    compra, seguimiento de pedidos, garantías y soporte.

    Args:
        identification: Número de identificación del cliente. En el flujo de
            negocio debe corresponder a un valor numérico de 4 a 11 dígitos.
        full_name: Nombre completo del cliente.
        phone: Número telefónico del cliente. En el flujo de negocio debe tener
            10 dígitos e iniciar por 3 o 6.
        email: Correo electrónico normalizado del cliente.
        kind: Clasificación comercial del cliente dentro del sistema. Por
            defecto se marca como `NEW`.

    Attributes:
        identification: Identificador único del cliente dentro del negocio.
        full_name: Nombre completo utilizado para personalizar la atención.
        phone: Teléfono de contacto asociado al cliente.
        email: Correo electrónico usado para contacto y notificaciones.
        kind: Tipo comercial del cliente, por ejemplo `NEW` o `FREQUENT`.

    Notes:
        `frozen=True` hace que la entidad sea inmutable después de creada.
        `slots=True` reduce el uso de memoria y evita agregar atributos
        dinámicos no definidos en la clase.
    """

    identification: str
    full_name: str
    phone: str
    email: str
    kind: CustomerKind = "NEW"
