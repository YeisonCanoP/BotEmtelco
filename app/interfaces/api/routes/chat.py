"""
Rutas HTTP para la conversación con el agente.

Este módulo expone el endpoint principal de chat. Recibe mensajes del usuario,
crea una sesión cuando no se proporciona una existente, delega el procesamiento
al servicio del agente y transforma errores de aplicación en respuestas HTTP.
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.application.dtos import AgentRequestDTO
from app.application.exceptions import (
    LLMServiceError,
    SessionStoreError,
)
from app.interfaces.api.deps import AgentDependency
from app.interfaces.api.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(request: ChatRequest, agent_service: AgentDependency) -> ChatResponse:
    """
    Procesa un mensaje enviado al agente conversacional.

    Si la solicitud no incluye un identificador de sesión, se genera uno nuevo.
    Luego se construye una solicitud de aplicación y se delega el procesamiento
    al servicio principal del agente.

    Args:
        request: Cuerpo HTTP con el mensaje del usuario y el identificador
            opcional de sesión.
        agent_service: Servicio del agente inyectado por FastAPI.

    Returns:
        ChatResponse: Respuesta del agente junto con el identificador de sesión.

    Raises:
        HTTPException: Retorna `503` cuando el almacenamiento de sesiones no
            está disponible.
        HTTPException: Retorna `502` cuando no es posible comunicarse con el
            proveedor del modelo de IA.
    """
    session_id = request.session_id or uuid4()

    logger.info(
        "Chat request recibido session_id=%s",
        session_id,
    )

    try:
        result = await agent_service.handle(
            AgentRequestDTO(
                session_id=session_id,
                message=request.message,
            )
        )

    except SessionStoreError as exc:
        logger.warning(
            "Chat request failed session_id=%s reason=session_store_error",
            session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de memoria no está disponible.",
        ) from exc

    except LLMServiceError as exc:
        logger.warning(
            "Chat request failed session_id=%s reason=llm_service_error",
            session_id,
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No fue posible comunicarse con el modelo de IA.",
        ) from exc

    return ChatResponse(
        session_id=result.session_id,
        reply=result.reply,
    )
