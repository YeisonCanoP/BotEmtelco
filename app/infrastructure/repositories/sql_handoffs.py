"""
Repositorio PostgreSQL para solicitudes generales de atención humana.

El adaptador persiste escalamiento conversacional independiente de garantías y
evita que una sesión acumule solicitudes activas duplicadas.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.exceptions import RepositoryError
from app.application.ports.repositories import HumanHandoffRepository
from app.domain.entities import (
    HumanHandoff,
    HumanHandoffReason,
    HumanHandoffStatus,
)
from app.infrastructure.db.models import HumanHandoffModel

ACTIVE_HANDOFF_STATUSES = frozenset(
    {
        HumanHandoffStatus.PENDING.value,
        HumanHandoffStatus.ASSIGNED.value,
    }
)


class SqlHumanHandoffRepository(HumanHandoffRepository):
    """Implementación SQLAlchemy del repositorio de atención humana."""

    def __init__(
        self,
        db: Session,
    ) -> None:
        """Inicializa el repositorio con la sesión de la petición."""

        self._db = db

    async def get_active_by_session(
        self,
        session_id: UUID,
    ) -> HumanHandoff | None:
        """Consulta la solicitud pendiente o asignada de una sesión."""

        statement = (
            select(HumanHandoffModel)
            .where(
                HumanHandoffModel.session_id == session_id,
                HumanHandoffModel.status.in_(ACTIVE_HANDOFF_STATUSES),
            )
            .order_by(
                HumanHandoffModel.created_at.desc(),
                HumanHandoffModel.id.desc(),
            )
            .limit(1)
        )

        try:
            model = self._db.scalar(statement)
        except SQLAlchemyError as exc:
            raise RepositoryError(
                "No fue posible consultar la solicitud de atención humana"
            ) from exc

        if model is None:
            return None

        return self._to_entity(model)

    async def create(
        self,
        handoff_id: str,
        session_id: UUID,
        customer_identification: str | None,
        reason: HumanHandoffReason,
        summary: str,
    ) -> tuple[HumanHandoff, bool]:
        """
        Crea una solicitud de atención humana.

        Si otra petición creó simultáneamente una solicitud activa para la
        sesión, se retorna esa solicitud en lugar de generar un duplicado.
        """

        model = HumanHandoffModel(
            id=handoff_id,
            session_id=session_id,
            customer_id=customer_identification,
            reason=reason.value,
            summary=summary,
            status=HumanHandoffStatus.PENDING.value,
        )

        self._db.add(model)

        try:
            self._db.commit()
            self._db.refresh(model)
        except IntegrityError as exc:
            self._db.rollback()

            existing = await self.get_active_by_session(session_id)

            if existing is not None:
                return existing, False

            raise RepositoryError("No fue posible crear la solicitud de atención humana") from exc
        except SQLAlchemyError as exc:
            self._db.rollback()
            raise RepositoryError("No fue posible crear la solicitud de atención humana") from exc

        return self._to_entity(model), True

    @staticmethod
    def _to_entity(
        model: HumanHandoffModel,
    ) -> HumanHandoff:
        """Convierte el modelo ORM en una entidad de dominio validada."""

        try:
            reason = HumanHandoffReason(model.reason)
            status = HumanHandoffStatus(model.status)
        except ValueError as exc:
            raise RepositoryError(
                "La solicitud de atención humana contiene un estado inválido"
            ) from exc

        return HumanHandoff(
            id=model.id,
            session_id=model.session_id,
            customer_id=model.customer_id,
            reason=reason,
            summary=model.summary,
            status=status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
