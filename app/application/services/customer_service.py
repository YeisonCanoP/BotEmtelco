"""
Casos de uso para consulta y registro de clientes.

Este módulo contiene la lógica de aplicación relacionada con clientes. Su
responsabilidad es coordinar la validación de datos, la consulta de clientes
existentes y el registro de clientes nuevos.

El servicio trabaja contra el puerto `CustomerRepository`, por lo que no depende
de una base de datos específica ni de una implementación concreta de
infraestructura.

Responsabilidades principales:

- Normalizar y validar la identificación del cliente.
- Consultar clientes existentes por identificación.
- Validar los datos requeridos para registrar clientes nuevos.
- Verificar duplicados por identificación y correo.
- Crear entidades de dominio `Customer`.
- Traducir conflictos de persistencia en resultados controlados.
"""

from dataclasses import dataclass
from typing import Literal

from app.application.exceptions import CustomerConflictError
from app.application.ports.repositories import CustomerRepository
from app.domain.entities import Customer
from app.domain.value_objects.contact import Email, Phone
from app.domain.value_objects.identity import (
    FullName,
    Identification,
)

CustomerConflictField = Literal[
    "identification",
    "email",
]


@dataclass(frozen=True, slots=True)
class CustomerRegistrationOutcome:
    """
    Resultado interno de un intento de registro de cliente.

    Este objeto permite representar de forma explícita si el registro terminó
    con éxito o si falló por un conflicto controlado de duplicidad.

    Si el cliente fue creado correctamente, `customer` contiene la entidad
    persistida y `conflict_field` queda en `None`.

    Si ocurrió un conflicto, `customer` queda en `None` y `conflict_field`
    indica qué campo generó el duplicado.

    Attributes:
        customer: Cliente creado correctamente. Es `None` cuando el registro no
            pudo completarse.
        conflict_field: Campo que produjo conflicto de unicidad. Puede ser
            `"identification"`, `"email"` o `None`.
    """

    customer: Customer | None
    conflict_field: CustomerConflictField | None = None

    @property
    def created(self) -> bool:
        """
        Indica si el cliente fue registrado correctamente.

        Returns:
            `True` si existe una entidad de cliente creada. De lo contrario,
            retorna `False`.
        """

        return self.customer is not None

    @property
    def has_conflict(self) -> bool:
        """
        Indica si el registro falló por un dato duplicado.

        Returns:
            `True` si existe un campo de conflicto. De lo contrario, retorna
            `False`.
        """

        return self.conflict_field is not None


class CustomerService:
    """
    Coordina los casos de uso relacionados con clientes.

    Este servicio pertenece a la capa de aplicación. Recibe datos crudos desde
    herramientas, endpoints o casos de uso, los valida mediante objetos de valor
    del dominio y delega el acceso a datos en `CustomerRepository`.

    No conoce detalles de SQLAlchemy, PostgreSQL, FastAPI ni Redis. Tampoco
    produce mensajes para el usuario final. Su salida son entidades de dominio o
    resultados estructurados que otras capas pueden interpretar.

    Attributes:
        _repository: Puerto utilizado para consultar y registrar clientes.
    """

    def __init__(
        self,
        repository: CustomerRepository,
    ) -> None:
        """
        Inicializa el servicio de clientes.

        Args:
            repository: Implementación del puerto `CustomerRepository` usada
                para consultar y registrar clientes.
        """

        self._repository = repository

    async def find_by_identification(
        self,
        identification: str,
    ) -> Customer | None:
        """
        Busca un cliente por identificación.

        Este métod normaliza y valida la identificación antes de consultar el
        repositorio. Se utiliza para determinar si el usuario corresponde a un
        cliente frecuente o si debe iniciar el flujo de registro.

        Args:
            identification: Identificación recibida desde una herramienta,
                endpoint o entrada conversacional.

        Returns:
            Cliente encontrado, o `None` si no existe un registro asociado.

        Raises:
            DomainError: Si la identificación no cumple las reglas del dominio.
            RepositoryError: Si ocurre un fallo al acceder al repositorio.
        """

        normalized_identification = Identification(identification).value

        return await self._repository.get_by_identification(normalized_identification)

    async def register(
        self,
        identification: str,
        full_name: str,
        phone: str,
        email: str,
    ) -> CustomerRegistrationOutcome:
        """
        Valida y registra un cliente nuevo.

        El métod primero normaliza y valida todos los datos requeridos usando
        objetos de valor del dominio. Después verifica si ya existe un cliente
        con la misma identificación o el mismo correo.

        Aunque se hacen validaciones previas, el repositorio también puede
        detectar conflictos durante la inserción. Esto protege el sistema ante
        condiciones de carrera, por ejemplo cuando dos peticiones intentan crear
        el mismo cliente al mismo tiempo.

        Args:
            identification: Identificación del cliente. Debe contener entre 4 y
                11 dígitos.
            full_name: Nombre completo del cliente. Solo debe contener letras,
                espacios, tildes y ñ.
            phone: Número telefónico del cliente. Debe tener exactamente 10
                dígitos e iniciar por 3 o 6.
            email: Correo electrónico del cliente.

        Returns:
            Resultado interno del registro. Si el cliente fue creado, contiene
            la entidad `Customer`. Si hubo conflicto, indica si el problema fue
            la identificación o el correo.

        Raises:
            DomainError: Si alguno de los datos no cumple las reglas del
                dominio.
            RepositoryError: Si ocurre un fallo de persistencia no relacionado
                con duplicados.
            CustomerConflictError: Si el repositorio reporta un campo de
                conflicto no reconocido.
        """

        normalized_identification = Identification(identification).value

        normalized_name = FullName(full_name).value

        normalized_phone = Phone(phone).value

        normalized_email = Email(email).value

        existing_customer = await self._repository.get_by_identification(normalized_identification)

        if existing_customer is not None:
            return CustomerRegistrationOutcome(
                customer=None,
                conflict_field="identification",
            )

        existing_email = await self._repository.get_by_email(normalized_email)

        if existing_email is not None:
            return CustomerRegistrationOutcome(
                customer=None,
                conflict_field="email",
            )

        customer = Customer(
            identification=normalized_identification,
            full_name=normalized_name,
            phone=normalized_phone,
            email=normalized_email,
            kind="NEW",
        )

        try:
            created_customer = await self._repository.create(customer)

        except CustomerConflictError as exc:
            if exc.field == "identification":
                return CustomerRegistrationOutcome(
                    customer=None,
                    conflict_field="identification",
                )

            if exc.field == "email":
                return CustomerRegistrationOutcome(
                    customer=None,
                    conflict_field="email",
                )

            raise

        return CustomerRegistrationOutcome(
            customer=created_customer,
        )
