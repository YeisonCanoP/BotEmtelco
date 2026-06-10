"""
Configuración de sesiones de base de datos.

Este módulo define la conexión principal de SQLAlchemy y la fábrica de
sesiones utilizada por la aplicación para acceder a la base de datos.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Crea y entrega una sesión de base de datos.

    La sesión se mantiene disponible durante la ejecución de la operación que
    la consume. Al finalizar, se cierra automáticamente para liberar la
    conexión asociada al pool de SQLAlchemy.

    Yields:
        Session: Sesión activa de SQLAlchemy.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
