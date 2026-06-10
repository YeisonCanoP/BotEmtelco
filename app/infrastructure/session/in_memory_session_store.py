from typing import Any


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    async def get(self, session_id: str) -> dict[str, Any]:
        return self._sessions.get(session_id, {}).copy()

    async def save(self, session_id: str, memory: dict[str, Any]) -> None:
        self._sessions[session_id] = memory.copy()
