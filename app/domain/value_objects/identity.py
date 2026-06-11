"""
Objetos de valor relacionados con la identidad de un cliente.

Este módulo define tipos pequeños e inmutables que encapsulan reglas de
validación propias del dominio para los datos de identificación del cliente.

Los objetos de valor permiten validar y normalizar datos antes de construir
entidades de dominio como `Customer`. De esta forma, las reglas centrales del
negocio no quedan dispersas en controladores, DTOs, repositorios o modelos ORM.
"""

import re
from dataclasses import dataclass

from app.domain.exceptions import DomainError

FULL_NAME_PATTERN = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$")


@dataclass(frozen=True, slots=True)
class Identification:
    """
    Identificación normalizada de un cliente.

    Este objeto de valor representa el número de identificación usado para
    validar clientes frecuentes o registrar clientes nuevos dentro del sistema.

    La identificación debe cumplir estas reglas:

    - Contener únicamente dígitos.
    - Tener mínimo 4 caracteres.
    - Tener máximo 11 caracteres.
    - No conservar espacios al inicio o al final.

    Attributes:
        value: Identificación normalizada del cliente.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Normaliza y valida la identificación recibida.

        Primero elimina espacios al inicio y al final. Luego valida que el valor
        contenga solo números y que su longitud esté dentro del rango permitido.

        Raises:
            DomainError: Si la identificación contiene caracteres no numéricos.
            DomainError: Si la identificación no tiene entre 4 y 11 dígitos.
        """

        normalized = self.value.strip()

        if not normalized.isdigit():
            raise DomainError("La identificación solo puede contener números")

        if not 4 <= len(normalized) <= 11:
            raise DomainError("La identificación debe contener entre 4 y 11 dígitos")

        object.__setattr__(
            self,
            "value",
            normalized,
        )


@dataclass(frozen=True, slots=True)
class FullName:
    """
    Nombre completo normalizado de un cliente.

    Este objeto de valor representa el nombre completo usado durante el registro
    o validación de clientes.

    El nombre completo debe cumplir estas reglas:

    - Tener mínimo 1 carácter.
    - Tener máximo 100 caracteres.
    - Permitir letras mayúsculas y minúsculas.
    - Permitir espacios entre palabras.
    - Permitir tildes, diéresis y la letra ñ.
    - No permitir números ni símbolos.

    Attributes:
        value: Nombre completo normalizado del cliente.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Normaliza y valida el nombre completo recibido.

        La normalización elimina espacios duplicados, espacios al inicio y
        espacios al final. Luego valida longitud y caracteres permitidos.

        Raises:
            DomainError: Si el nombre no tiene entre 1 y 100 caracteres.
            DomainError: Si el nombre contiene números, símbolos o caracteres no
                permitidos.
        """

        normalized = " ".join(self.value.split())

        if not 1 <= len(normalized) <= 100:
            raise DomainError("El nombre completo debe contener entre 1 y 100 caracteres")

        if FULL_NAME_PATTERN.fullmatch(normalized) is None:
            raise DomainError("El nombre completo solo puede contener letras y espacios")

        object.__setattr__(
            self,
            "value",
            normalized,
        )
