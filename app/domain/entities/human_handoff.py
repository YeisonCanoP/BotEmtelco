"""
Entidad de dominio para solicitudes generales de atención humana.

Este módulo modela el escalamiento de una conversación a un asesor humano sin
vincularlo obligatoriamente con un pedido, una garantía o un ticket técnico.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class HumanHandoffReason(StrEnum):
    """
    Motivos permitidos para solicitar atención humana.

    Attributes:
        USER_REQUEST: El usuario pidió explícitamente hablar con una persona.
        INTENT_NOT_UNDERSTOOD: El agente pidió una aclaración y aun así no pudo
            identificar la intención del usuario.
    """

    USER_REQUEST = "USER_REQUEST"
    INTENT_NOT_UNDERSTOOD = "INTENT_NOT_UNDERSTOOD"


class HumanHandoffStatus(StrEnum):
    """
    Estados permitidos para una solicitud de atención humana.

    Attributes:
        PENDING: Solicitud creada y pendiente de asignación.
        ASSIGNED: Solicitud asignada a un asesor.
        CLOSED: Solicitud finalizada.
    """

    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    CLOSED = "CLOSED"


@dataclass(frozen=True, slots=True)
class HumanHandoff:
    """
    Solicitud general de transferencia a un asesor humano.

    La entidad conserva la sesión que originó la solicitud y, cuando existe un
    cliente verificado, su identificación. El cliente es opcional porque pedir
    atención humana no requiere completar un flujo de identificación.

    Attributes:
        id: Identificador público de la solicitud.
        session_id: Sesión conversacional que originó el escalamiento.
        customer_id: Cliente verificado asociado, si existe.
        reason: Motivo controlado del escalamiento.
        summary: Resumen concreto de la necesidad expresada por el usuario.
        status: Estado actual de atención.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última actualización.
    """

    id: str
    session_id: UUID
    customer_id: str | None
    reason: HumanHandoffReason
    summary: str
    status: HumanHandoffStatus
    created_at: datetime
    updated_at: datetime
