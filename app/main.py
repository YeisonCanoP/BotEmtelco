"""
Punto de entrada de FastAPI.

Este módulo crea y configura la instancia principal de la aplicación.
Inicializa la configuración global, registra el sistema de logging,
valida la conexión con Redis durante el arranque, agrega middlewares
HTTP e incluye las rutas principales de la API.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.cache.redis_client import (
    close_redis_client,
    get_redis_client,
)
from app.infrastructure.config import get_settings
from app.infrastructure.logging_config import configure_logging
from app.interfaces.api.middleware.request_logging import (
    RequestLoggingMiddleware,
)
from app.interfaces.api.routes.routers import api_router

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
) -> AsyncGenerator[None]:
    """
    Gestiona el ciclo de vida de la aplicación.

    Durante el arranque registra información básica del entorno, valida la
    conexión con Redis y deja lista la aplicación para recibir solicitudes.
    Durante el apagado cierra el cliente Redis y registra el cierre del servicio.

    Args:
        _app: Instancia de FastAPI administrada por el ciclo de vida.

    Yields:
        None: Control de ejecución entregado a FastAPI mientras la aplicación
        permanece activa.
    """
    logger.info(
        "Application starting environment=%s model=%s",
        settings.app_env,
        settings.openai_model,
    )

    redis_client = get_redis_client()
    await redis_client.ping()

    logger.info("Redis connection established")

    try:
        yield
    finally:
        await close_redis_client()
        logger.info("Redis connection closed")
        logger.info("Application shutting down")


app = FastAPI(
    title="Agente de prueba técnica Emtelco",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.include_router(api_router)
