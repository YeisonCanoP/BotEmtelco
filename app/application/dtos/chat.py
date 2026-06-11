"""
DTOs utilizados por el flujo conversacional del agente.

Este módulo define los modelos de transferencia de datos relacionados con
mensajes, sesiones conversacionales y solicitudes/respuestas del servicio
principal del agente.

Los DTOs permiten normalizar la comunicación entre la capa de entrada
por ejemplo, endpoints HTTP, la capa de aplicación y los casos de uso del
agente, evitando exponer directamente modelos internos o entidades de dominio.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """
    Roles permitidos para los mensajes dentro de una conversación.

    El rol indica quién produjo cada mensaje dentro del historial
    conversacional. Esta información es necesaria para reconstruir el contexto
    enviado al modelo de lenguaje y diferenciar los mensajes del usuario de las
    respuestas generadas por el asistente.

    Attributes:
        USER: Mensaje enviado por el usuario final.
        ASSISTANT: Mensaje generado por el agente o asistente.
    """

    USER = "user"
    ASSISTANT = "assistant"


class ChatMessageDTO(BaseModel):
    """
    Representa un mensaje individual dentro de una conversación.

    Cada mensaje contiene el rol del emisor y el contenido textual asociado.
    Este DTO se utiliza para almacenar, transportar y reconstruir el historial
    conversacional de una sesión.

    Attributes:
        role: Rol del autor del mensaje. Puede ser `user` o `assistant`.
        content: Contenido textual del mensaje. Debe tener al menos un carácter
            y no superar los 20.000 caracteres.
    """

    role: MessageRole
    content: str = Field(
        min_length=1,
        max_length=20_000,
    )


class ConversationDTO(BaseModel):
    """
    Representa el estado persistente de una conversación.

    Este DTO agrupa el identificador único de la sesión y el historial visible
    de mensajes intercambiados entre el usuario y el asistente. Sirve para
    conservar el contexto conversacional a lo largo de la sesión.

    Attributes:
        session_id: Identificador único de la sesión conversacional.
        messages: Lista ordenada de mensajes asociados a la conversación.
    """

    session_id: UUID
    messages: list[ChatMessageDTO] = Field(default_factory=list)


class AgentRequestDTO(BaseModel):
    """
    Representa la entrada del caso de uso principal del agente.

    Este DTO se usa cuando el usuario envía un nuevo mensaje al agente. Incluye
    la sesión a la que pertenece el mensaje y el texto que debe procesarse.

    Attributes:
        session_id: Identificador de la sesión asociada al mensaje del usuario.
        message: Mensaje enviado por el usuario. Debe tener al menos un carácter
            y no superar los 4.000 caracteres.
    """

    session_id: UUID
    message: str = Field(
        min_length=1,
        max_length=4_000,
    )


class AgentResponseDTO(BaseModel):
    """
    Representa la respuesta final generada por el agente.

    Este DTO se retorna después de procesar el mensaje del usuario, ejecutar la
    lógica conversacional y, si aplica, invocar herramientas externas como
    catálogo, pedidos o garantías.

    Attributes:
        session_id: Identificador de la sesión asociada a la respuesta.
        reply: Texto final que será entregado al usuario.
    """

    session_id: UUID
    reply: str = Field(min_length=1)
