"""Estado estructurado disponible durante una solicitud del agente."""

from dataclasses import dataclass


@dataclass(slots=True)
class ConversationContext:
    """Cliente validado para la conversación actual."""

    customer_id: str | None = None
    customer_name: str | None = None

    @property
    def is_customer_verified(self) -> bool:
        return self.customer_id is not None

    def verify_customer(self, identification: str, full_name: str) -> None:
        self.customer_id = identification
        self.customer_name = full_name

    def clear_customer(self) -> None:
        self.customer_id = None
        self.customer_name = None
