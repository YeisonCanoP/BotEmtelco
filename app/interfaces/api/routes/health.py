"""
Rutas de verificación de estado de la aplicación.

Este módulo expone endpoints simples para validar que la API esté disponible
y que la conexión con la base de datos funcione correctamente.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.db.session import get_db

router = APIRouter(
    tags=["health"],
)


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "Agente IA Retail",
        "status": "running",
        "docs": "/docs",
    }


@router.get("/health")
async def health() -> dict[str, str]:
    """
    Verifica que la API esté disponible.

    Returns:
        dict[str, str]: Estado general de la aplicación.
    """
    return {"status": "ok"}


@router.get("/health_database")
def health_database(db: Session = Depends(get_db)) -> dict[str, str]:
    """
    Verifica la conexión con la base de datos.

    Ejecuta una consulta mínima contra la base de datos para confirmar que
    la sesión puede conectarse y responder correctamente.

    Args:
        db (Session): Sesión activa de SQLAlchemy inyectada por FastAPI.

    Returns:
        dict[str, str]: Estado de la aplicación y de la conexión a la base de datos.
    """
    db.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }
