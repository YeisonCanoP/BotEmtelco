"""
Repositorio PostgreSQL para consulta y registro de clientes.

Este módulo contiene la implementación concreta del puerto
`CustomerRepository` usando SQLAlchemy y PostgreSQL.

El repositorio trabaja con modelos ORM para persistencia, pero expone entidades
de dominio para que el resto de la aplicación no dependa de SQLAlchemy.

Responsabilidades principales:

- Consultar clientes por identificación.
- Consultar clientes por correo electrónico.
- Registrar clientes nuevos.
- Detectar conflictos de unicidad al crear clientes.
- Convertir modelos ORM en entidades de dominio.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.exceptions import (
    CustomerConflictError,
    RepositoryError,
)
from app.application.ports.repositories import CustomerRepository
from app.domain.entities import Customer, is_customer_kind
from app.infrastructure.db.models import CustomerModel


class SqlCustomerRepository(CustomerRepository):
    """
    Implementación PostgreSQL del repositorio de clientes.

    Esta clase adapta el contrato `CustomerRepository` a una base de datos
    relacional usando SQLAlchemy.

    La sesión de base de datos es recibida por inyección de dependencias y debe
    estar asociada al ciclo de vida de una única petición HTTP. El repositorio
    no crea ni cierra la sesión; solo la utiliza para ejecutar consultas,
    confirmar escrituras o revertir transacciones cuando ocurre un error.

    Attributes:
        _db: Sesión SQLAlchemy activa usada para consultar y persistir clientes.
    """

    def __init__(self, db: Session) -> None:
        """
        Inicializa el repositorio con una sesión de base de datos.

        Args:
            db: Sesión SQLAlchemy activa. Normalmente es creada por la capa de
                infraestructura y entregada mediante inyección de dependencias.
        """

        self._db = db

    async def get_by_identification(
        self,
        identification: str,
    ) -> Customer | None:
        """
        Busca un cliente por su identificación.

        Este métod consulta la clave primaria de la tabla `customers`.
        Se utiliza para validar si un cliente ya existe antes de ejecutar
        operaciones asociadas a pedidos, garantías o registro de cliente nuevo.

        Args:
            identification: Identificación normalizada del cliente.

        Returns:
            Entidad de dominio `Customer` si existe un cliente con esa
            identificación. Retorna `None` si no se encuentra ningún registro.

        Raises:
            RepositoryError: Si ocurre un error inesperado al consultar la base
                de datos.
        """

        try:
            model = self._db.get(
                CustomerModel,
                identification,
            )
        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar el cliente") from exc

        if model is None:
            return None

        return self._to_entity(model)

    async def get_by_email(
        self,
        email: str,
    ) -> Customer | None:
        """
        Busca un cliente por correo electrónico.

        Este métod permite validar duplicados durante el registro de clientes
        nuevos o recuperar un cliente cuando el correo es el dato disponible en
        la conversación.

        Args:
            email: Correo electrónico normalizado, preferiblemente en
                minúsculas.

        Returns:
            Entidad de dominio `Customer` si existe un cliente con ese correo.
            Retorna `None` si no se encuentra ningún registro.

        Raises:
            RepositoryError: Si ocurre un error inesperado al consultar la base
                de datos.
        """

        statement = select(CustomerModel).where(
            CustomerModel.email == email,
        )

        try:
            model = self._db.scalar(statement)
        except SQLAlchemyError as exc:
            raise RepositoryError("No fue posible consultar el correo del cliente") from exc

        if model is None:
            return None

        return self._to_entity(model)

    async def create(
        self,
        customer: Customer,
    ) -> Customer:
        """
        Registra un cliente nuevo en la base de datos.

        La entidad recibida debe llegar validada y normalizada desde la capa de
        aplicación. Este repositorio solo se encarga de persistirla y convertir
        posibles errores de infraestructura en excepciones propias de la
        aplicación.

        Aunque la aplicación valide previamente que la identificación y el
        correo no existan, PostgreSQL conserva la decisión final sobre la
        unicidad. Esto protege contra condiciones de carrera cuando dos
        peticiones intentan crear el mismo cliente al mismo tiempo.

        Args:
            customer: Entidad de dominio con los datos del cliente que se desea
                registrar.

        Returns:
            Cliente persistido convertido nuevamente a entidad de dominio.

        Raises:
            CustomerConflictError: Si la identificación o el correo ya existen
                en la base de datos.
            RepositoryError: Si ocurre otro error de persistencia.
        """

        model = CustomerModel(
            identification=customer.identification,
            full_name=customer.full_name,
            phone=customer.phone,
            email=customer.email,
            kind=customer.kind,
        )

        self._db.add(model)

        try:
            self._db.commit()
            self._db.refresh(model)

        except IntegrityError as exc:
            self._db.rollback()

            conflict_field = self._get_conflict_field(exc)

            if conflict_field is not None:
                raise CustomerConflictError(conflict_field) from exc

            raise RepositoryError("No fue posible registrar el cliente") from exc

        except SQLAlchemyError as exc:
            self._db.rollback()

            raise RepositoryError("No fue posible registrar el cliente") from exc

        return self._to_entity(model)

    @staticmethod
    def _get_conflict_field(
        error: IntegrityError,
    ) -> str | None:
        """
        Identifica el campo que produjo un conflicto de unicidad.

        PostgreSQL expone información diagnóstica en el error original. Esta
        función inspecciona el nombre de la restricción violada para traducir un
        error técnico de base de datos a un campo entendible por la capa de
        aplicación.

        Restricciones esperadas:

        - `customers_pkey`: conflicto por identificación duplicada.
        - `customers_email_key`: conflicto por correo duplicado.

        Args:
            error: Error de integridad emitido por SQLAlchemy.

        Returns:
            Nombre lógico del campo duplicado. Puede ser `"identification"` o
            `"email"`. Retorna `None` si la restricción no corresponde a un
            conflicto conocido.
        """

        original_error = error.orig
        diagnostic = getattr(original_error, "diag", None)
        constraint_name = getattr(
            diagnostic,
            "constraint_name",
            None,
        )

        if constraint_name == "customers_pkey":
            return "identification"

        if constraint_name == "customers_email_key":
            return "email"

        return None

    @staticmethod
    def _to_entity(
        model: CustomerModel,
    ) -> Customer:
        """
        Convierte un modelo ORM en una entidad de dominio.

        Esta conversión evita que las capas superiores trabajen directamente
        con objetos SQLAlchemy. El repositorio recibe y devuelve entidades del
        dominio, mientras que los modelos ORM quedan encapsulados dentro de la
        infraestructura.

        Args:
            model: Instancia de `CustomerModel` recuperada o persistida mediante
                SQLAlchemy.

        Returns:
            Entidad `Customer` independiente de la infraestructura.
        """

        if not is_customer_kind(model.kind):
            raise RepositoryError(
                f"Clasificación de cliente inválida en persistencia: {model.kind!r}"
            )

        return Customer(
            identification=model.identification,
            full_name=model.full_name,
            phone=model.phone,
            email=model.email,
            kind=model.kind,
        )
