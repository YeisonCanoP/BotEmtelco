"""
Middleware de logging para solicitudes HTTP.

Este módulo registra información básica de cada solicitud procesada por la API,
incluyendo identificador de request, métod HTTP, ruta, código de respuesta y
tiempo total de ejecución.
"""

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware para registrar el ciclo de vida de las solicitudes HTTP.

    Genera o reutiliza un identificador de solicitud mediante el header
    `X-Request-ID`, mide el tiempo de procesamiento y agrega el identificador
    a la respuesta HTTP.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """
        Procesa una solicitud HTTP y registra su resultado.

        Args:
            request: Solicitud HTTP entrante.
            call_next: Función que continúa el procesamiento de la solicitud
                hacia el siguiente middleware o endpoint.

        Returns:
            Response: Respuesta HTTP generada por la aplicación.

        Raises:
            Exception: Relanza cualquier excepción producida durante el
                procesamiento de la solicitud después de registrarla en logs.
        """
        request_id = request.headers.get(
            "X-Request-ID",
            str(uuid4()),
        )
        started_at = perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP request failed request_id=%s method=%s path=%s",
                request_id,
                request.method,
                request.url.path,
            )
            raise

        duration_ms = (perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "HTTP request completed request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
