"""
Configuración general de la aplicación.

Este módulo centraliza la lectura y validación de variables de entorno usadas
por la API, la base de datos, Redis, logging y el proveedor de inteligencia
artificial.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
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

    openai_temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Parámetro de muestreo por temperatura. No debe usarse junto con top_p.",
    )

    openai_top_p: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Parámetro de muestreo nucleus sampling. No debe usarse junto con temperature.",
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

    @field_validator(
        "openai_temperature",
        "openai_top_p",
        mode="before",
    )
    def empty_sampling_value_to_none(
        self,
        value: object,
    ) -> object:
        """
        Convierte valores vacíos de muestreo en `None`.

        Permite que variables de entorno vacías para `OPENAI_TEMPERATURE`
        u `OPENAI_TOP_P` sean interpretadas como valores no configurados.

        Args:
            value: Valor recibido desde la configuración.

        Returns:
            object: `None` si el valor es un string vacío; de lo contrario,
            retorna el valor original.
        """
        if isinstance(value, str) and not value.strip():
            return None

        return value

    @model_validator(mode="after")
    def validate_sampling_parameters(self) -> "Settings":
        """
        Valida que no se configuren simultáneamente `temperature` y `top_p`.

        Returns:
            Settings: Instancia de configuración validada.

        Raises:
            ValueError: Si `openai_temperature` y `openai_top_p` tienen valor
            al mismo tiempo.
        """
        if self.openai_temperature is not None and self.openai_top_p is not None:
            raise ValueError("Configura OPENAI_TEMPERATURE o OPENAI_TOP_P, pero no ambos.")

        return self

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
