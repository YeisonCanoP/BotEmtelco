class AgentService:
    async def handle(self, message: str, session_id: str) -> str:
        raise NotImplementedError
