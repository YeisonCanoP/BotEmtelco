"""
Configuración centralizada de logging.

Este módulo define la configuración global de logs de la aplicación,
incluyendo salida por consola y escritura en archivo con rotación.
"""

from logging.config import dictConfig

from app.infrastructure.config import Settings


def configure_logging(settings: Settings) -> None:
    """
    Configura el sistema de logging de la aplicación.

    Crea el directorio de logs si no existe y registra una configuración
    centralizada para enviar logs tanto a consola como a un archivo rotativo.

    Args:
        settings: Configuración de la aplicación con los parámetros de logging,
            como nivel, directorio, nombre del archivo, tamaño máximo y cantidad
            de respaldos.

    Returns:
        None.
    """
    settings.log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = settings.log_directory / settings.log_filename
    level = settings.log_level.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": ("%(asctime)s | %(levelname)s | %(name)s | %(message)s"),
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": level,
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": level,
                    "formatter": "standard",
                    "filename": str(log_file),
                    "maxBytes": settings.log_max_bytes,
                    "backupCount": settings.log_backup_count,
                    "encoding": "utf-8",
                },
            },
            "root": {
                "level": level,
                "handlers": ["console", "file"],
            },
            "loggers": {
                "openai": {"level": "WARNING"},
                "httpx": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
            },
        }
    )
