"""
DTOs utilizados para identificación y registro de clientes.

Este módulo define los modelos de entrada y salida usados por las herramientas
o servicios encargados de validar clientes frecuentes y registrar clientes
nuevos dentro del flujo conversacional del agente.

Los DTOs cumplen tres responsabilidades principales:

- Normalizar datos recibidos desde la conversación.
- Validar reglas de entrada antes de ejecutar casos de uso.
- Retornar resultados estructurados para que el agente pueda decidir el
    siguiente paso de la conversación.

Las validaciones de formato se delegan a objetos de valor del dominio, como
`Identification`, `FullName`, `Phone` y `Email`, para evitar duplicar reglas en
la capa de aplicación.
"""

from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.domain.entities import CustomerKind
from app.domain.value_objects.contact import Email, Phone
from app.domain.value_objects.identity import (
    FullName,
    Identification,
)


class CustomerLookupInputDTO(BaseModel):
    """
    Entrada requerida para buscar un cliente existente.

    Este DTO se utiliza cuando el agente necesita validar si una identificación
    ya pertenece a un cliente registrado. Aplica para clientes frecuentes o para
    comprobar si un usuario debe iniciar el flujo de registro.

    Attributes:
        identification: Identificación del cliente compuesta por entre 4 y 11
            dígitos numéricos.
    """

    model_config = ConfigDict(extra="forbid")

    identification: str = Field(
        min_length=4,
        max_length=11,
        description="Identificación del cliente compuesta por entre 4 y 11 dígitos.",
    )

    @field_validator("identification")
    @classmethod
    def normalize_identification(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza y valida la identificación del cliente.

        La validación se delega al objeto de valor `Identification`, que elimina
        espacios externos y verifica que el dato contenga únicamente números
        con la longitud permitida.

        Args:
            value: Identificación recibida desde la entrada del usuario.

        Returns:
            Identificación normalizada.

        Raises:
            DomainError: Si la identificación no cumple las reglas del dominio.
        """

        return Identification(value).value


class CustomerRegistrationInputDTO(CustomerLookupInputDTO):
    """
    Datos requeridos para registrar un cliente nuevo.

    Este DTO extiende la entrada de búsqueda porque el registro también requiere
    una identificación válida. Además, incorpora los datos obligatorios de
    contacto y nombre del cliente.

    Attributes:
        identification: Identificación del cliente.
        full_name: Nombre completo del cliente.
        phone: Teléfono de contacto del cliente.
        email: Correo electrónico del cliente.
    """

    full_name: str = Field(
        min_length=1,
        max_length=100,
        description="Nombre completo. Solo admite letras, espacios, tildes y ñ.",
    )

    phone: str = Field(
        min_length=10,
        max_length=10,
        description="Teléfono de 10 dígitos que comienza por 3 o 6.",
    )

    email: str = Field(
        min_length=3,
        max_length=150,
        description="Correo electrónico del cliente.",
    )

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza y valida el nombre completo del cliente.

        La validación se delega al objeto de valor `FullName`, que elimina
        espacios duplicados y verifica longitud y caracteres permitidos.

        Args:
            value: Nombre completo recibido desde la entrada del usuario.

        Returns:
            Nombre completo normalizado.

        Raises:
            DomainError: Si el nombre contiene caracteres no permitidos o no
                cumple la longitud definida.
        """

        return FullName(value).value

    @field_validator("phone")
    @classmethod
    def normalize_phone(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza y valida el teléfono del cliente.

        La validación se delega al objeto de valor `Phone`, que verifica que el
        número tenga exactamente 10 dígitos y comience por 3 o 6.

        Args:
            value: Teléfono recibido desde la entrada del usuario.

        Returns:
            Teléfono normalizado.

        Raises:
            DomainError: Si el teléfono no cumple las reglas del dominio.
        """

        return Phone(value).value

    @field_validator("email")
    @classmethod
    def normalize_email(
        cls,
        value: str,
    ) -> str:
        """
        Normaliza y valida el correo electrónico del cliente.

        La validación se delega al objeto de valor `Email`, que convierte el
        correo a minúsculas y verifica longitud, formato y reglas básicas de
        estructura.

        Args:
            value: Correo electrónico recibido desde la entrada del usuario.

        Returns:
            Correo electrónico normalizado.

        Raises:
            DomainError: Si el correo no tiene un formato válido.
        """

        return Email(value).value


class CustomerResultDTO(BaseModel):
    """
    Información mínima de un cliente retornada al agente.

    Este DTO se usa como salida segura para confirmar que un cliente fue
    encontrado o registrado. No incluye teléfono ni correo porque esos datos no
    son necesarios para continuar la conversación y no deben exponerse si no
    aportan al flujo.

    Attributes:
        identification: Identificación validada del cliente.
        full_name: Nombre completo del cliente.
        kind: Clasificación del cliente dentro del flujo comercial.
    """

    identification: str = Field(
        pattern=r"^[0-9]{4,11}$",
    )

    full_name: str = Field(
        min_length=1,
        max_length=100,
    )

    kind: CustomerKind


class CustomerLookupResultDTO(BaseModel):
    """
    Resultado estructurado de la búsqueda de un cliente.

    Este DTO permite que el agente sepa si la identificación corresponde a un
    cliente existente o si debe continuar con el flujo de registro.

    Attributes:
        success: Indica si la operación de búsqueda se ejecutó correctamente.
        found: Indica si el cliente fue encontrado.
        customer: Información mínima del cliente encontrado.
        requires_registration: Indica si el usuario debe completar registro.
    """

    success: bool = True
    found: bool
    customer: CustomerResultDTO | None = None
    requires_registration: bool

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba la consistencia del resultado de búsqueda.

        Reglas de consistencia:

        - Si `found` es `True`, debe existir información en `customer`.
        - Si `found` es `False`, `customer` debe ser `None`.
        - `requires_registration` debe ser el valor contrario de `found`.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.found and self.customer is None:
            raise ValueError("Un cliente encontrado debe incluir información")

        if not self.found and self.customer is not None:
            raise ValueError("Un cliente no encontrado no puede incluir información")

        if self.requires_registration == self.found:
            raise ValueError("requires_registration debe ser contrario a found")

        return self


class CustomerRegistrationResultDTO(BaseModel):
    """
    Resultado estructurado del registro de un cliente.

    Este DTO permite representar tanto registros exitosos como conflictos
    controlados por identificación o correo duplicado.

    Attributes:
        success: Indica si la operación terminó exitosamente.
        created: Indica si el cliente fue creado.
        customer: Información mínima del cliente creado.
        conflict_field: Campo que produjo conflicto de unicidad, si aplica.
    """

    success: bool
    created: bool
    customer: CustomerResultDTO | None = None

    conflict_field: (
        Literal[
            "identification",
            "email",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Comprueba la consistencia del resultado de registro.

        Reglas de consistencia:

        - Si `created` es `True`, `success` también debe ser `True`.
        - Si `created` es `True`, debe existir información en `customer`.
        - Si el registro fue creado, no puede existir `conflict_field`.
        - Si existe `conflict_field`, la operación no puede ser exitosa.
        - Si existe `conflict_field`, no debe existir un cliente nuevo.

        Returns:
            Instancia validada.

        Raises:
            ValueError: Si el resultado contiene una combinación inconsistente
                de campos.
        """

        if self.created:
            if not self.success:
                raise ValueError("Un registro creado debe ser exitoso")

            if self.customer is None:
                raise ValueError("Un registro creado debe incluir el cliente")

            if self.conflict_field is not None:
                raise ValueError("Un registro creado no puede tener conflictos")

        if self.conflict_field is not None:
            if self.success or self.created:
                raise ValueError("Un conflicto no puede representar un registro exitoso")

            if self.customer is not None:
                raise ValueError("Un conflicto no puede incluir un cliente nuevo")

        return self
