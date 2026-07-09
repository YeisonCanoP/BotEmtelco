"""
Configuración de sesiones de base de datos.

Este módulo define la conexión principal de SQLAlchemy y la fábrica de
sesiones utilizada por la aplicación para acceder a la base de datos.

La conexión es asíncrona: se apoya en `psycopg` (psycopg3), que soporta el
modo async de forma nativa. Esto evita bloquear el event loop de la API cuando
una consulta a PostgreSQL está en curso.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infrastructure.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Crea y entrega una sesión asíncrona de base de datos.

    La sesión se mantiene disponible durante la ejecución de la operación que
    la consume. Al finalizar, se cierra automáticamente para liberar la
    conexión asociada al pool de SQLAlchemy.

    Yields:
        AsyncSession: Sesión activa de SQLAlchemy en modo asíncrono.
    """
    async with SessionLocal() as db:
        yield db
