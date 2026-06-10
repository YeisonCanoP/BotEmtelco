"""
Raíz de composición de dependencias para las rutas de la API.

Este módulo centraliza la inyección de dependencias usadas por los endpoints.
Define cómo obtener una sesión de base de datos y cómo construir los servicios
de infraestructura requeridos por la capa de aplicación.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports.llm_provider import LLMProvider
from app.application.ports.repositories import CatalogRepository
from app.application.ports.session_store import SessionStore
from app.application.services.agent_service import AgentService
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.config import get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.repositories.sql_catalog import SqlCatalogRepository
from app.infrastructure.session.redis_session_store import RedisSessionStore

DbSession = Annotated[Session, Depends(get_db)]


def get_catalog_repository(db: DbSession) -> CatalogRepository:
    """
    Construye el repositorio de catálogo usado por la API.

    Args:
        db: Sesión activa de SQLAlchemy inyectada por FastAPI.

    Returns:
        CatalogRepository: Repositorio de catálogo conectado a PostgreSQL.
    """
    return SqlCatalogRepository(db)


CatalogDependency = Annotated[
    CatalogRepository,
    Depends(get_catalog_repository),
]


@lru_cache
def get_session_store() -> SessionStore:
    """
    Construye el almacenamiento de sesiones conversacionales.

    Usa Redis como implementación concreta para conservar el contexto de las
    conversaciones del agente durante la sesión, incluyendo información como
    cliente, productos consultados, presupuesto, último pedido y preferencias.

    Returns:
        SessionStore: Almacenamiento de sesiones respaldado por Redis.
    """
    settings = get_settings()

    return RedisSessionStore(
        client=get_redis_client(),
        ttl_seconds=settings.redis_session_ttl_seconds,
        key_prefix=settings.redis_session_prefix,
    )


@lru_cache
def get_llm_provider() -> LLMProvider:
    """Construye el proveedor de OpenAI."""
    return OpenAIProvider()


def get_agent_service(
    llm_provider: Annotated[
        LLMProvider,
        Depends(get_llm_provider),
    ],
    session_store: Annotated[
        SessionStore,
        Depends(get_session_store),
    ],
) -> AgentService:
    """Construye el servicio conversacional."""

    return AgentService(
        llm_provider=llm_provider,
        session_store=session_store,
    )


AgentDependency = Annotated[
    AgentService,
    Depends(get_agent_service),
]
