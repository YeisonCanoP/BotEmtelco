"""
Cliente Redis de la aplicación.

Este módulo centraliza la creación y cierre del cliente Redis usado por la
aplicación para almacenar información temporal, como sesiones conversacionales,
estado de contexto o datos de soporte requeridos durante la interacción del
agente.
"""

from functools import lru_cache

from redis.asyncio import Redis

from app.infrastructure.config import get_settings


@lru_cache
def get_redis_client() -> Redis:
    """
    Obtiene una instancia reutilizable del cliente Redis.

    La instancia se crea una sola vez y se mantiene en caché para evitar abrir
    múltiples conexiones innecesarias durante la ejecución de la aplicación.

    Returns:
        Redis: Cliente Redis configurado con la URL definida en settings.
    """
    settings = get_settings()

    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


async def close_redis_client() -> None:
    """
    Cierra el cliente Redis almacenado en caché.

    Si el cliente aún no ha sido creado, la función termina sin ejecutar
    ninguna acción. Cuando existe una instancia activa, se cierra la conexión
    y se limpia la caché para permitir una nueva inicialización posterior.

    Returns:
        None.
    """
    if get_redis_client.cache_info().currsize == 0:
        return

    client = get_redis_client()
    await client.aclose()
    get_redis_client.cache_clear()
