"""
Almacenamiento Redis para sesiones conversacionales.

Este módulo implementa el puerto `SessionStore` usando Redis como backend de
persistencia temporal. Permite guardar y recuperar el estado de una conversación
del agente a partir de su identificador de sesión.
"""

import logging
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.application.dtos import ConversationDTO
from app.application.exceptions import SessionStoreError
from app.application.ports.session_store import SessionStore

logger = logging.getLogger(__name__)


class RedisSessionStore(SessionStore):
    """
    Implementación Redis del almacenamiento de sesiones conversacionales.

    Guarda cada conversación como un JSON serializado en Redis, usando una clave
    construida a partir de un prefijo configurable y el identificador de sesión.
    Cada registro se almacena con un tiempo de vida para evitar conservar
    sesiones indefinidamente.
    """

    def __init__(
        self,
        client: Redis,
        ttl_seconds: int,
        key_prefix: str,
    ) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix.rstrip(":")

    def _build_key(self, session_id: UUID) -> str:
        """
        Construye la clave Redis asociada a una sesión.

        Args:
            session_id: Identificador único de la sesión conversacional.

        Returns:
            str: Clave Redis usada para almacenar o consultar la conversación.
        """
        return f"{self._key_prefix}:{session_id}"

    async def get(
        self,
        session_id: UUID,
    ) -> ConversationDTO | None:
        """
        Recupera una conversación almacenada en Redis.

        Args:
            session_id: Identificador único de la sesión conversacional.

        Returns:
            ConversationDTO | None: Conversación encontrada, o `None` si no existe.

        Raises:
            SessionStoreError: Si ocurre un error al consultar Redis o si el
                contenido almacenado no puede convertirse a `ConversationDTO`.
        """
        key = self._build_key(session_id)

        try:
            payload = await self._client.get(key)

        except RedisError as exc:
            logger.exception(
                "Redis session read failed session_id=%s",
                session_id,
            )

            raise SessionStoreError("No fue posible consultar la conversación") from exc

        if payload is None:
            logger.debug(
                "No fue posible consultar la conversación session_id=%s",
                session_id,
            )
            return None

        try:
            conversation = ConversationDTO.model_validate_json(payload)
        except ValueError as exc:
            logger.exception(
                "Invalid session payload session_id=%s",
                session_id,
            )
            raise SessionStoreError("La conversación almacenada no es válida") from exc

        logger.debug(
            "Sesión cargada session_id=%s messages=%s",
            session_id,
            len(conversation.messages),
        )

        return conversation

    async def save(
        self,
        conversation: ConversationDTO,
    ) -> None:
        """
        Guarda una conversación en Redis.

        La conversación se serializa como JSON y se almacena con tiempo de vida
        configurado para que expire automáticamente.

        Args:
            conversation: Conversación normalizada que debe guardarse.

        Raises:
            SessionStoreError: Si ocurre un error al escribir la conversación
                en Redis.
        """
        key = self._build_key(conversation.session_id)
        payload = conversation.model_dump_json()

        try:
            await self._client.set(
                name=key,
                value=payload,
                ex=self._ttl_seconds,
            )

        except RedisError as exc:
            logger.exception(
                "Redis session write failed session_id=%s",
                conversation.session_id,
            )
            raise SessionStoreError("No fue posible guardar la conversación") from exc

        logger.debug(
            "Se guardó la conversación session_id=%s messages=%s ttl_seconds=%s",
            conversation.session_id,
            len(conversation.messages),
            self._ttl_seconds,
        )
