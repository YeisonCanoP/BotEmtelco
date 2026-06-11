"""
DTOs para solicitar atención humana desde una conversación.

Los modelos de este módulo exponen al agente únicamente el motivo controlado y
un resumen del caso. La sesión y el cliente se obtienen desde el contexto
interno y nunca se reciben como argumentos del modelo de lenguaje.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.entities import (
    HumanHandoffReason,
    HumanHandoffStatus,
)


class HumanHandoffInputDTO(BaseModel):
    """
    Entrada para solicitar atención humana.

    Attributes:
        reason: Motivo controlado por el que se solicita un asesor.
        summary: Resumen concreto de lo que necesita el usuario.
    """

    model_config = ConfigDict(extra="forbid")

    reason: HumanHandoffReason = Field(
        description=(
            "Motivo del escalamiento. Usa USER_REQUEST cuando el usuario pide "
            "una persona e INTENT_NOT_UNDERSTOOD solo después de una aclaración fallida."
        ),
    )

    summary: str = Field(
        min_length=10,
        max_length=1_000,
        description="Resumen breve y concreto de la necesidad expresada por el usuario.",
    )

    @field_validator("summary")
    @classmethod
    def normalize_summary(
        cls,
        value: str,
    ) -> str:
        """Normaliza espacios repetidos dentro del resumen."""

        return " ".join(value.split())


class HumanHandoffDTO(BaseModel):
    """
    Solicitud de atención humana expuesta de forma segura al agente.

    No incluye identificación del cliente ni detalles internos de la sesión.
    """

    id: str = Field(
        min_length=1,
        max_length=40,
        pattern=r"^HND-[A-F0-9]{32}$",
    )

    reason: HumanHandoffReason

    summary: str = Field(
        min_length=10,
        max_length=1_000,
    )

    status: HumanHandoffStatus


class HumanHandoffResultDTO(BaseModel):
    """
    Resultado de solicitar atención humana.

    `escalated` indica que se creó una solicitud nueva. `already_pending`
    indica que la sesión ya tenía una solicitud activa y no se creó un
    duplicado.
    """

    success: bool
    escalated: bool
    already_pending: bool
    handoff: HumanHandoffDTO

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """Valida que el resultado describa una solicitud activa consistente."""

        if not self.success:
            raise ValueError("El resultado de escalamiento debe ser exitoso")

        if self.escalated == self.already_pending:
            raise ValueError("El resultado debe indicar creación nueva o solicitud pendiente")

        if self.handoff.status not in {
            HumanHandoffStatus.PENDING,
            HumanHandoffStatus.ASSIGNED,
        }:
            raise ValueError("La solicitud retornada debe estar activa")

        return self
