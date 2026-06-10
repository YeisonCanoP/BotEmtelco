"""
Puerto para almacenar sesiones conversacionales.

Este módulo define el contrato de persistencia para guardar y recuperar el
estado de una conversación del agente. Esto permite conservar contexto durante
la sesión, como datos del cliente, productos consultados, presupuesto,
último pedido y preferencias expresadas. :contentReference[oaicite:0]{index=0}
"""

from typing import Protocol
from uuid import UUID

from app.application.dtos import ConversationDTO


class SessionStore(Protocol):
    """
    Contrato de persistencia para conversaciones.

    Define las operaciones necesarias para consultar y guardar el estado de una
    sesión conversacional sin acoplar la aplicación a una implementación
    concreta de almacenamiento.
    """

    async def get(
        self,
        session_id: UUID,
    ) -> ConversationDTO | None:
        """
        Busca una conversación por su identificador.

        Args:
            session_id: Identificador único de la sesión conversacional.

        Returns:
            ConversationDTO | None: Conversación encontrada, o `None` si no existe.
        """
        ...

    async def save(
        self,
        conversation: ConversationDTO,
    ) -> None:
        """
        Guarda el estado actualizado de una conversación.

        Args:
            conversation: Conversación normalizada que debe persistirse.

        Returns:
            None.
        """
        ...
