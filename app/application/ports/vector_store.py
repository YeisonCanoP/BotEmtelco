from typing import Protocol

from app.domain.value_objects.knowledge_chunk import KnowledgeChunk


class VectorStore(Protocol):
    async def search(self, embedding: list[float], limit: int) -> list[KnowledgeChunk]: ...

    async def upsert(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> None: ...
