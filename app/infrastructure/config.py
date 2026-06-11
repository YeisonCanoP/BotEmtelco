"""
Configuración general de la aplicación.

Este módulo centraliza la lectura y validación de variables de entorno usadas
por la API, la base de datos, Redis, logging y el proveedor de inteligencia
artificial.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """
    Configuración cargada desde variables de entorno.

    Los valores pueden provenir del archivo `.env` ubicado en la raíz del
    proyecto o de variables de entorno del sistema.
    """

    app_env: str = Field(
        default="development",
        description="Entorno de ejecución de la aplicación.",
    )
    api_base_url: str = Field(
        default="http://localhost:8000",
        description="URL base pública o local de la API.",
    )

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5433/retail_ai",
        description="Cadena de conexión a la base de datos PostgreSQL.",
    )

    openai_api_key: str = Field(
        default="",
        description="API key usada para autenticarse con OpenAI.",
    )
    openai_model: str = Field(
        default="gpt-5-mini",
        description="Modelo de OpenAI usado por el agente conversacional.",
    )

    openai_reasoning_effort: Literal[
        "minimal",
        "low",
        "medium",
        "high",
    ] = Field(
        default="low",
        description="Nivel de esfuerzo de razonamiento solicitado al modelo.",
    )

    openai_verbosity: Literal[
        "low",
        "medium",
        "high",
    ] = Field(
        default="low",
        description="Nivel de detalle esperado en las respuestas del modelo.",
    )

    openai_max_output_tokens: int = Field(
        default=800,
        ge=1,
        le=128_000,
        description="Cantidad máxima de tokens permitidos en la respuesta del modelo.",
    )

    openai_timeout_seconds: float = Field(
        default=60,
        gt=0,
        description="Tiempo máximo de espera, en segundos, para llamadas a OpenAI.",
    )
    openai_max_retries: int = Field(
        default=2,
        ge=0,
        le=10,
        description="Número máximo de reintentos permitidos ante errores del proveedor LLM.",
    )

    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Modelo usado para generar embeddings.",
    )

    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL de conexión a Redis.",
    )
    redis_session_ttl_seconds: int = Field(
        default=86_400,
        description="Tiempo de vida, en segundos, de las sesiones conversacionales en Redis.",
    )
    redis_session_prefix: str = Field(
        default="retail-ai:session",
        description="Prefijo usado para construir claves de sesión en Redis.",
    )

    log_level: str = Field(
        default="INFO",
        description="Nivel mínimo de logs que debe registrar la aplicación.",
    )
    log_directory: Path = Field(
        default=BASE_DIR / "logs",
        description="Directorio donde se almacenan los archivos de logs.",
    )
    log_filename: str = Field(
        default="app.log",
        description="Nombre del archivo principal de logs.",
    )
    log_max_bytes: int = Field(
        default=5_000_000,
        description="Tamaño máximo, en bytes, del archivo de logs antes de rotarlo.",
    )
    log_backup_count: int = Field(
        default=5,
        description="Cantidad máxima de archivos históricos de logs que se conservan.",
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Obtiene la configuración de la aplicación.

    La instancia se mantiene en caché para evitar cargar y validar las variables
    de entorno en cada uso.

    Returns:
        Settings: Configuración validada de la aplicación.
    """
    return Settings()
