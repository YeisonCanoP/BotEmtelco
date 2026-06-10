from typing import Any, Protocol


class SessionStore(Protocol):
    async def get(self, session_id: str) -> dict[str, Any]: ...

    async def save(self, session_id: str, memory: dict[str, Any]) -> None: ...
