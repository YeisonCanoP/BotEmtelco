"""
Entidad de dominio para reclamos de garantía.

Este módulo define la entidad `WarrantyClaim`, que representa un caso de soporte
técnico registrado después de validar que un producto pertenece al cliente y
que cuenta con garantía vigente.

Un reclamo funciona como ticket técnico para hacer seguimiento del caso desde
su creación hasta su resolución, rechazo o escalamiento a un asesor humano.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class WarrantyClaimStatus(StrEnum):
    """
    Estados permitidos para un reclamo de garantía.

    Este enum representa el ciclo de vida de un reclamo o ticket técnico dentro
    del sistema de soporte.

    Los valores deben coincidir con la restricción definida en PostgreSQL para
    evitar inconsistencias entre el dominio y la persistencia.

    Attributes:
        OPEN: Reclamo creado y pendiente de revisión inicial.
        IN_REVIEW: Reclamo en proceso de análisis por soporte técnico.
        ESCALATED: Reclamo escalado a un asesor humano o equipo especializado.
        RESOLVED: Reclamo resuelto correctamente.
        REJECTED: Reclamo rechazado porque no cumple las condiciones de
            garantía o soporte.
    """

    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class WarrantyClaim:
    """
    Reclamo o ticket técnico asociado a una garantía.

    Esta entidad representa el caso registrado cuando un cliente reporta un
    problema sobre un producto cubierto por garantía. El reclamo queda asociado
    a una garantía específica y al cliente propietario del pedido.

    El identificador del reclamo también funciona como número de ticket. Esto
    evita mantener dos identificadores distintos para el mismo caso y facilita
    que el agente entregue una referencia clara al usuario.

    Al ser una entidad de dominio:

    - No conoce cómo se almacena el reclamo.
    - No ejecuta consultas ni actualizaciones en base de datos.
    - No depende de modelos ORM.
    - No genera respuestas conversacionales.
    - Puede ser usada por servicios, repositorios y herramientas del agente.

    Attributes:
        id: Identificador único del reclamo. También funciona como número de
            ticket de soporte.
        warranty_id: Identificador de la garantía asociada al reclamo.
        customer_id: Identificación del cliente propietario del pedido y del
            reclamo.
        description: Descripción normalizada del problema reportado por el
            cliente.
        status: Estado actual del reclamo dentro del flujo de garantía.
        requires_human: Indica si el caso debe ser atendido o revisado por un
            asesor humano.
        escalation_reason: Motivo registrado al escalar el caso. Es `None`
            mientras el reclamo no haya sido escalado.
        created_at: Fecha y hora en la que se creó el reclamo.
        updated_at: Fecha y hora de la última actualización del reclamo.

    Notes:
        `frozen=True` hace que la entidad sea inmutable después de creada.
        `slots=True` evita atributos dinámicos y reduce el uso de memoria.
    """

    id: str
    warranty_id: str
    customer_id: str
    description: str
    status: WarrantyClaimStatus
    requires_human: bool
    escalation_reason: str | None
    created_at: datetime
    updated_at: datetime
