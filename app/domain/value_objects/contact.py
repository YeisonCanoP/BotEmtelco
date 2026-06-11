"""
Objetos de valor relacionados con los datos de contacto.

Este módulo define objetos de valor inmutables para validar y normalizar la
información de contacto de un cliente.

Los objetos de valor permiten concentrar reglas propias del dominio antes de
crear entidades como `Customer`. Así se evita repetir validaciones en DTOs,
repositorios, modelos ORM o herramientas del agente.

Reglas cubiertas:

- Teléfono con exactamente 10 dígitos.
- Teléfono iniciado en 3 o 6.
- Correo electrónico normalizado en minúsculas.
- Correo con longitud y formato válidos.
"""

import re
from dataclasses import dataclass

from app.domain.exceptions import DomainError

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
    r"@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


@dataclass(frozen=True, slots=True)
class Phone:
    """
    Número telefónico normalizado de un cliente.

    Este objeto de valor representa el teléfono usado para contactar al cliente
    durante flujos de registro, pedidos, garantías o soporte.

    El número telefónico debe cumplir estas reglas:

    - Contener únicamente dígitos.
    - Tener exactamente 10 dígitos.
    - Iniciar por 3 o 6.
    - No conservar espacios al inicio o al final.

    Attributes:
        value: Número telefónico normalizado.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Normaliza y valida el número telefónico recibido.

        Primero elimina espacios al inicio y al final. Luego valida que el valor
        contenga solo números, tenga exactamente 10 dígitos e inicie por uno de
        los prefijos permitidos.

        Raises:
            DomainError: Si el teléfono contiene caracteres no numéricos.
            DomainError: Si el teléfono no tiene exactamente 10 dígitos.
            DomainError: Si el teléfono no inicia por 3 o 6.
        """

        normalized = self.value.strip()

        if not normalized.isdigit():
            raise DomainError("El teléfono solo puede contener números")

        if len(normalized) != 10:
            raise DomainError("El teléfono debe contener exactamente 10 dígitos")

        if normalized[0] not in {"3", "6"}:
            raise DomainError("El teléfono debe comenzar por 3 o 6")

        object.__setattr__(
            self,
            "value",
            normalized,
        )


@dataclass(frozen=True, slots=True)
class Email:
    """
    Dirección de correo electrónico normalizada de un cliente.

    Este objeto de valor representa el correo usado para identificar, contactar
    o validar duplicados durante el registro de clientes.

    El correo se normaliza en minúsculas para evitar que direcciones iguales
    sean tratadas como diferentes por variaciones entre mayúsculas y minúsculas.

    El correo debe cumplir estas reglas:

    - Tener entre 3 y 150 caracteres.
    - Contener un formato válido con `@` y dominio.
    - No iniciar ni terminar la parte local con punto.
    - No contener puntos consecutivos en la parte local ni en el dominio.

    Attributes:
        value: Correo electrónico normalizado.
    """

    value: str

    def __post_init__(self) -> None:
        """
        Normaliza y valida el correo electrónico recibido.

        Primero elimina espacios al inicio y al final, y convierte el valor a
        minúsculas. Después valida longitud, formato general y reglas básicas
        adicionales para evitar correos mal formados.

        Raises:
            DomainError: Si el correo no tiene entre 3 y 150 caracteres.
            DomainError: Si el correo no cumple el formato esperado.
            DomainError: Si la parte local inicia o termina con punto.
            DomainError: Si existen puntos consecutivos en la parte local o en
                el dominio.
        """

        normalized = self.value.strip().lower()

        if not 3 <= len(normalized) <= 150:
            raise DomainError("El correo debe contener entre 3 y 150 caracteres")

        if EMAIL_PATTERN.fullmatch(normalized) is None:
            raise DomainError("El correo electrónico no tiene un formato válido")

        local_part, _, domain = normalized.partition("@")

        if local_part.startswith(".") or local_part.endswith("."):
            raise DomainError("El correo electrónico no tiene un formato válido")

        if ".." in local_part or ".." in domain:
            raise DomainError("El correo electrónico no tiene un formato válido")

        object.__setattr__(
            self,
            "value",
            normalized,
        )
