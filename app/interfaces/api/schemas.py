"""
Esquemas HTTP de la API.

Este módulo define los modelos Pydantic usados para validar las solicitudes
entrantes y estructurar las respuestas salientes del endpoint de chat.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    Solicitud recibida por el endpoint de chat.

    Representa el mensaje enviado por el usuario al agente conversacional.
    Si no se envía un `session_id`, la API puede crear una nueva sesión para
    iniciar una conversación.

    Attributes:
        message: Mensaje del usuario que será procesado por el agente.
        session_id: Identificador opcional de la sesión conversacional.
    """

    message: str = Field(
        min_length=1,
        max_length=4_000,
    )
    session_id: UUID | None = None


class ChatResponse(BaseModel):
    """
    Respuesta retornada por el endpoint de chat.

    Contiene el identificador de la sesión y el texto generado por el agente
    conversacional.

    Attributes:
        session_id: Identificador de la sesión asociada a la conversación.
        reply: Respuesta generada por el agente.
    """

    session_id: UUID
    reply: str
