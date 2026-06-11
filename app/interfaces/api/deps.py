"""
Raíz de composición de dependencias para las rutas de la API.

Este módulo centraliza la inyección de dependencias usadas por los endpoints.
Construye repositorios, herramientas, proveedores externos y servicios de
aplicación sin acoplar la lógica del agente a FastAPI o a detalles concretos
de infraestructura.

Responsabilidades:
- Obtener la sesión de base de datos por solicitud.
- Construir el repositorio SQL del catálogo.
- Construir el registro de herramientas disponibles para el agente.
- Construir el almacenamiento Redis de sesiones conversacionales.
- Construir el proveedor LLM basado en OpenAI.
- Construir el servicio principal del agente conversacional.
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports.llm_provider import LLMProvider
from app.application.ports.repositories import CatalogRepository
from app.application.ports.session_store import SessionStore
from app.application.services.agent_service import AgentService
from app.application.tools import (
    CompareProductsTool,
    SearchCatalogTool,
    ToolRegistry,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.config import get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.repositories.sql_catalog import SqlCatalogRepository
from app.infrastructure.session.redis_session_store import RedisSessionStore

DbSession = Annotated[
    Session,
    Depends(get_db),
]


def get_catalog_repository(
    db: DbSession,
) -> CatalogRepository:
    """
    Construye el repositorio de catálogo usado por la API.

    El repositorio se crea por solicitud porque depende de una sesión de base
    de datos administrada por FastAPI.

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


def get_tool_registry(
    catalog_repository: CatalogDependency,
) -> ToolRegistry:
    """
    Construye el registro de herramientas disponibles para el agente.

    Este registro no debe almacenarse en caché porque sus herramientas dependen
    del repositorio de catálogo, y ese repositorio usa una sesión de base de
    datos asociada a la solicitud HTTP actual.

    Args:
        catalog_repository: Repositorio usado por las herramientas de catálogo.

    Returns:
        ToolRegistry: Registro con herramientas disponibles para el agente.
    """
    return ToolRegistry(
        tools=[
            SearchCatalogTool(catalog_repository),
            CompareProductsTool(catalog_repository),
        ]
    )


ToolRegistryDependency = Annotated[
    ToolRegistry,
    Depends(get_tool_registry),
]


@lru_cache
def get_session_store() -> SessionStore:
    """
    Construye el almacenamiento de sesiones conversacionales.

    Usa Redis como implementación concreta para conservar el contexto de las
    conversaciones del agente durante la sesión.

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
    """
    Construye el proveedor LLM de la aplicación.

    La instancia se mantiene en caché porque el cliente de OpenAI puede
    reutilizarse entre solicitudes.

    Returns:
        LLMProvider: Adaptador configurado de OpenAI.
    """
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
    tool_registry: ToolRegistryDependency,
) -> AgentService:
    """
    Construye el servicio principal del agente conversacional.

    Integra memoria conversacional, proveedor LLM y herramientas disponibles
    para procesar mensajes del usuario.

    Args:
        llm_provider: Proveedor usado para generar respuestas del modelo.
        session_store: Almacenamiento usado para recuperar y guardar sesiones.
        tool_registry: Registro de herramientas disponibles para el agente.

    Returns:
        AgentService: Servicio principal del agente con memoria, LLM y herramientas.
    """
    settings = get_settings()

    return AgentService(
        llm_provider=llm_provider,
        session_store=session_store,
        tool_registry=tool_registry,
        max_tool_rounds=settings.agent_max_tool_rounds,
    )


AgentDependency = Annotated[
    AgentService,
    Depends(get_agent_service),
]
