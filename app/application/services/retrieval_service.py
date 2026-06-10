from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.vector_store import VectorStore
from app.domain.value_objects.knowledge_chunk import KnowledgeChunk


class RetrievalService:
    def __init__(self, embeddings: EmbeddingProvider, vector_store: VectorStore) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store

    async def retrieve(
        self, query: str, k: int = 4, threshold: float = 0.7
    ) -> list[KnowledgeChunk]:
        embedding = (await self._embeddings.embed([query]))[0]
        chunks = await self._vector_store.search(embedding, k)
        return [chunk for chunk in chunks if chunk.score is None or chunk.score >= threshold]
