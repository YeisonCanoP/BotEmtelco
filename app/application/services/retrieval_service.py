"""
Servicio de recuperación semántica para la base de conocimiento.

Este módulo define el servicio encargado de recuperar fragmentos relevantes
desde la base de conocimiento a partir de una consulta textual.

El flujo de recuperación se divide en dos pasos:

    1. Generar un embedding para la consulta del usuario.
    2. Buscar en el almacenamiento vectorial los fragmentos más similares.


Responsabilidades principales:
    - Normalizar la consulta recibida.
    - Validar que la consulta no esté vacía.
    - Controlar el límite máximo de fragmentos solicitados.
    - Generar el embedding de la consulta.
    - Ejecutar la búsqueda vectorial.
    - Filtrar resultados por un umbral mínimo de similitud.

"""

import logging

from app.application.exceptions import KnowledgeServiceError
from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.vector_store import VectorStore
from app.domain.value_objects import KnowledgeChunk

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Servicio de recuperación semántica de fragmentos de conocimiento.

    Coordina la generación del embedding de una consulta y la búsqueda de
    fragmentos similares dentro del almacenamiento vectorial.

    La clase aplica un umbral mínimo de similitud para evitar devolver
    fragmentos poco relevantes al agente. Solo se retornan fragmentos cuyo
    `score` sea mayor o igual a `score_threshold`.

    Attributes:
        _embeddings: Proveedor usado para convertir texto en vectores.
        _vector_store: Almacenamiento vectorial usado para buscar fragmentos.
        _score_threshold: Puntaje mínimo de similitud requerido para aceptar un
            fragmento como relevante.
        _score_margin: Diferencia máxima permitida respecto al mejor resultado.

    Raises:
        ValueError: Si `score_threshold` no está entre 0.0 y 1.0.
    """

    def __init__(
        self,
        embeddings: EmbeddingProvider,
        vector_store: VectorStore,
        score_threshold: float = 0.30,
        score_margin: float = 0.10,
    ) -> None:
        """
        Inicializa el servicio de recuperación.

        Args:
            embeddings: Puerto para generar embeddings de texto.
            vector_store: Puerto para consultar la base de conocimiento
                vectorial.
            score_threshold: Puntaje mínimo de similitud requerido para retornar
                un fragmento. Debe estar entre 0.0 y 1.0.
            score_margin: Diferencia máxima permitida respecto al fragmento con
                mayor similitud. Debe estar entre 0.0 y 1.0.

        Raises:
            ValueError: Si `score_threshold` está fuera del rango permitido.
        """

        if not 0.0 <= score_threshold <= 1.0:
            raise ValueError("score_threshold debe estar entre 0 y 1")

        if not 0.0 <= score_margin <= 1.0:
            raise ValueError("score_margin debe estar entre 0 y 1")

        self._embeddings = embeddings
        self._vector_store = vector_store
        self._score_threshold = score_threshold
        self._score_margin = score_margin

    async def retrieve(
        self,
        query: str,
        limit: int = 4,
    ) -> list[KnowledgeChunk]:
        """
        Recupera fragmentos relevantes para una consulta.

        Primero normaliza la consulta eliminando espacios repetidos, saltos de
        línea y tabulaciones internas. Luego genera un embedding para esa
        consulta y lo usa para buscar fragmentos similares en el almacenamiento
        vectorial.

        El límite solicitado se normaliza entre 1 y 8 para evitar búsquedas
        demasiado amplias desde el agente o desde una herramienta.

        Finalmente, los fragmentos se filtran con un umbral adaptativo. El
        resultado debe superar el mínimo absoluto y permanecer cerca del mejor
        score encontrado. Esto tolera consultas con errores ortográficos sin
        incluir temas claramente menos relacionados.

        Args:
            query: Pregunta, necesidad o texto que se desea resolver usando la
                base de conocimiento.
            limit: Cantidad máxima de fragmentos solicitados.

        Returns:
            Lista de fragmentos cuyo score supera o iguala el umbral configurado.

        Raises:
            KnowledgeServiceError: Si la consulta queda vacía después de
                normalizarse.
            KnowledgeServiceError: Si el proveedor de embeddings no retorna
                exactamente un vector válido para la consulta.
        """

        normalized_query = " ".join(query.split())

        if not normalized_query:
            raise KnowledgeServiceError("La consulta de conocimiento no puede estar vacía")

        normalized_limit = max(1, min(limit, 8))

        embeddings = await self._embeddings.embed([normalized_query])

        if len(embeddings) != 1 or not embeddings[0]:
            raise KnowledgeServiceError("No fue posible generar el embedding de la consulta")

        chunks = await self._vector_store.search(
            embedding=embeddings[0],
            limit=normalized_limit,
        )

        scored_chunks = [chunk for chunk in chunks if chunk.score is not None]

        if not scored_chunks:
            return []

        best_score = max(chunk.score for chunk in scored_chunks if chunk.score is not None)
        adaptive_threshold = max(
            self._score_threshold,
            best_score - self._score_margin,
        )

        results = [
            chunk
            for chunk in scored_chunks
            if chunk.score is not None and chunk.score >= adaptive_threshold
        ]

        logger.info(
            "Knowledge results filtered candidates=%s accepted=%s best_score=%.4f threshold=%.4f",
            len(scored_chunks),
            len(results),
            best_score,
            adaptive_threshold,
        )

        return results
