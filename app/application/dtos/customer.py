"""DTOs para identificación y registro de clientes."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.value_objects.contact import Email, Phone
from app.domain.value_objects.identity import FullName, Identification


class CustomerLookupInputDTO(BaseModel):
    """Identificación requerida para buscar un cliente."""

    model_config = ConfigDict(extra="forbid")

    identification: str = Field(
        min_length=4,
        max_length=11,
        description="Identificación del cliente, compuesta por 4 a 11 dígitos.",
    )

    @field_validator("identification")
    @classmethod
    def validate_identification(cls, value: str) -> str:
        normalized = value.strip()
        Identification(normalized)
        return normalized


class CustomerRegistrationInputDTO(CustomerLookupInputDTO):
    """Datos requeridos para registrar un cliente nuevo."""

    full_name: str = Field(
        min_length=1,
        max_length=100,
        description="Nombre completo; solo letras, espacios, tildes y ñ.",
    )
    phone: str = Field(
        min_length=10,
        max_length=10,
        description="Teléfono de 10 dígitos que inicia en 3 o 6.",
    )
    email: str = Field(
        min_length=3,
        max_length=150,
        description="Correo electrónico válido.",
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        FullName(normalized)
        return normalized

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = value.strip()
        Phone(normalized)
        return normalized

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        Email(normalized)
        return normalized


class CustomerResultDTO(BaseModel):
    """Información mínima de un cliente identificado."""

    identification: str
    full_name: str
    kind: str


class CustomerLookupResultDTO(BaseModel):
    """Resultado de la búsqueda de un cliente."""

    success: bool = True
    found: bool
    customer: CustomerResultDTO | None = None
    requires_registration: bool


class CustomerRegistrationResultDTO(BaseModel):
    """Resultado del registro de un cliente."""

    success: bool
    created: bool
    customer: CustomerResultDTO | None = None
    conflict_field: str | None = None
