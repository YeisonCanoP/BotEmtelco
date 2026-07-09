"""
Script para generar los embeddings pendientes de la base de conocimiento.

El script consulta los registros de `kb_chunks` cuyo embedding es NULL,
genera sus vectores mediante el proveedor configurado y los guarda en
PostgreSQL usando pgvector.

Puede ejecutarse varias veces. Los fragmentos que ya tengan embedding no
se vuelven a procesar.
"""

import argparse
import asyncio
import logging

from app.application.exceptions import KnowledgeServiceError
from app.domain.value_objects import (
    KnowledgeChunk,
    KnowledgeChunkEmbedding,
)
from app.infrastructure.config import get_settings
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.llm.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from app.infrastructure.logging_config import configure_logging
from app.infrastructure.vectorstore.pgvector_store import PgVectorStore

logger = logging.getLogger(__name__)


def build_embedding_text(
    chunk: KnowledgeChunk,
) -> str:
    """
    Construye el texto que será convertido en embedding.

    El título se incluye junto con el contenido para mejorar la recuperación
    cuando la consulta del usuario coincida con el tema general del fragmento.

    Args:
        chunk: Fragmento pendiente de vectorización.

    Returns:
        Texto preparado para generar el embedding.
    """

    return f"{chunk.title}\n\n{chunk.text}"


async def ingest_pending_knowledge(
    batch_size: int,
) -> int:
    """
    Genera y guarda los embeddings pendientes.

    Los fragmentos se procesan por lotes para evitar enviar demasiados textos
    en una sola petición al proveedor.

    Args:
        batch_size: Cantidad máxima de fragmentos procesados por lote.

    Returns:
        Cantidad total de fragmentos indexados.

    Raises:
        KnowledgeServiceError: Si un fragmento no tiene identificador o si el
            proveedor retorna una cantidad inesperada de embeddings.
    """

    settings = get_settings()
    embedding_provider = OpenAIEmbeddingProvider(settings)
    total_indexed = 0

    async with SessionLocal() as db:
        vector_store = PgVectorStore(
            db=db,
            settings=settings,
        )

        while True:
            chunks = await vector_store.list_without_embeddings(
                limit=batch_size,
            )

            if not chunks:
                break

            texts = [build_embedding_text(chunk) for chunk in chunks]

            vectors = await embedding_provider.embed(texts)

            if len(vectors) != len(chunks):
                raise KnowledgeServiceError(
                    "La cantidad de embeddings no coincide con los fragmentos"
                )

            pending_embeddings: list[KnowledgeChunkEmbedding] = []

            for chunk, vector in zip(
                chunks,
                vectors,
                strict=True,
            ):
                if chunk.id is None:
                    raise KnowledgeServiceError(
                        "No es posible indexar un fragmento sin identificador"
                    )

                pending_embeddings.append(
                    KnowledgeChunkEmbedding(
                        chunk_id=chunk.id,
                        embedding=tuple(vector),
                    )
                )

            await vector_store.save_embeddings(pending_embeddings)

            total_indexed += len(pending_embeddings)

            logger.info(
                "Knowledge batch indexed batch=%s total=%s",
                len(pending_embeddings),
                total_indexed,
            )

    return total_indexed


def parse_arguments() -> argparse.Namespace:
    """
    Lee y valida los argumentos de la línea de comandos.

    Returns:
        Argumentos validados del script.
    """

    parser = argparse.ArgumentParser(
        description="Genera embeddings para kb_chunks pendientes.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Cantidad de fragmentos procesados por lote.",
    )

    arguments = parser.parse_args()

    if not 1 <= arguments.batch_size <= 1_000:
        parser.error("--batch-size debe estar entre 1 y 1000")

    return arguments


def main() -> None:
    """Ejecuta el proceso de indexación."""

    settings = get_settings()
    configure_logging(settings)
    arguments = parse_arguments()

    try:
        total_indexed = asyncio.run(
            ingest_pending_knowledge(
                batch_size=arguments.batch_size,
            )
        )
    except (KnowledgeServiceError, ValueError) as exc:
        logger.error(
            "Knowledge ingestion failed: %s",
            exc,
        )
        raise SystemExit(1) from exc

    logger.info(
        "Knowledge ingestion completed indexed=%s",
        total_indexed,
    )


if __name__ == "__main__":
    main()
