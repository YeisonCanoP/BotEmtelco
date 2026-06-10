from uuid import uuid4

from fastapi import APIRouter, status

from app.interfaces.api.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    return ChatResponse(
        session_id=session_id,
        reply="El agente todavía no está conectado. Estructura base creada correctamente.",
    )
