"""
Implementación PostgreSQL y pgvector del almacenamiento vectorial.

Este módulo implementa el puerto `VectorStore` usando PostgreSQL como motor de
persistencia y pgvector como extensión para búsqueda semántica.

El adaptador trabaja sobre la tabla `kb_chunks`, donde se almacenan fragmentos
de la base de conocimiento junto con sus embeddings. Permite consultar
fragmentos similares, listar fragmentos pendientes de vectorización y guardar
embeddings generados previamente.

Responsabilidades principales:
    - Buscar fragmentos usando distancia coseno con pgvector.
    - Convertir la distancia coseno en un score de similitud.
    - Listar fragmentos cuyo embedding todavía es NULL.
    - Persistir embeddings sobre registros existentes.
    - Validar que los vectores tengan la dimensión configurada.
    - Convertir modelos ORM en objetos de valor del dominio.

"""

import logging
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.exceptions import KnowledgeServiceError
from app.application.ports.vector_store import VectorStore
from app.domain.value_objects import (
    KnowledgeChunk,
    KnowledgeChunkEmbedding,
)
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.db.models import KnowledgeChunkModel

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStore):
    """
    Implementación del puerto `VectorStore` usando PostgreSQL y pgvector.

    Esta clase encapsula las operaciones necesarias para trabajar con una base
    de conocimiento vectorial almacenada en PostgreSQL.

    La búsqueda semántica se realiza mediante distancia coseno sobre la columna
    `embedding` del modelo `KnowledgeChunkModel`. Como pgvector retorna
    distancia y la aplicación espera similitud, el adaptador transforma el valor
    mediante:

        score = 1 - distance

    Attributes:
        _db: Sesión SQLAlchemy activa para ejecutar consultas y transacciones.
        _dimensions: Dimensión esperada para cada embedding.
    """

    def __init__(
        self,
        db: Session,
        settings: Settings | None = None,
    ) -> None:
        """
        Inicializa el almacenamiento vectorial.

        Args:
            db: Sesión SQLAlchemy activa.
            settings: Configuración opcional de la aplicación. Si no se
                proporciona, se obtiene mediante `get_settings`.
        """

        self._db = db
        self._dimensions = (settings or get_settings()).embedding_dimensions

    async def search(
        self,
        embedding: list[float],
        limit: int,
    ) -> list[KnowledgeChunk]:
        """
        Busca fragmentos ordenados por similitud coseno.

        pgvector retorna distancia coseno, no similitud:

            - 0 representa máxima similitud.
            - 1 representa mínima similitud entre vectores normalizados.

        Para que el resto de la aplicación trabaje con una escala más natural,
        este adaptador convierte la distancia en score de similitud usando:

            score = 1 - distance

        El score final se limita al rango entre 0.0 y 1.0 para evitar valores
        fuera de rango por diferencias numéricas del motor de base de datos.

        Args:
            embedding: Vector semántico de la consulta.
            limit: Cantidad máxima de resultados solicitados.

        Returns:
            Lista de fragmentos ordenados de mayor a menor similitud.

        Raises:
            KnowledgeServiceError: Si el embedding está vacío.
            KnowledgeServiceError: Si el embedding no coincide con la dimensión
                configurada.
            KnowledgeServiceError: Si PostgreSQL no puede ejecutar la consulta.

        """

        self._validate_embedding(embedding)

        normalized_limit = max(1, min(limit, 50))

        cosine_distance = KnowledgeChunkModel.embedding.cosine_distance(
            embedding,
        )

        statement = (
            select(
                KnowledgeChunkModel,
                cosine_distance.label("distance"),
            )
            .where(
                KnowledgeChunkModel.embedding.is_not(None),
            )
            .order_by(cosine_distance)
            .limit(normalized_limit)
        )

        try:
            rows = self._db.execute(statement).all()

        except SQLAlchemyError as exc:
            raise KnowledgeServiceError("No fue posible consultar la base de conocimiento") from exc

        results: list[KnowledgeChunk] = []

        for model, distance in rows:
            numeric_distance = float(distance)
            score = max(
                0.0,
                min(1.0, 1.0 - numeric_distance),
            )

            results.append(
                self._to_chunk(
                    model=model,
                    score=score,
                )
            )

        logger.info(
            "Vector search completed results=%s limit=%s",
            len(results),
            normalized_limit,
        )

        return results

    async def list_without_embeddings(
        self,
        limit: int = 100,
    ) -> list[KnowledgeChunk]:
        """
        Lista fragmentos que aún no han sido vectorizados.

        Esta operación se usa normalmente en procesos de indexación o
        sincronización de la base de conocimiento. Permite encontrar registros
        existentes en `kb_chunks` cuyo campo `embedding` todavía es NULL.

        Args:
            limit: Cantidad máxima de registros pendientes que se deben
                retornar.

        Returns:
            Lista de fragmentos cuyo campo `embedding` es NULL.

        Raises:
            KnowledgeServiceError: Si PostgreSQL no puede ejecutar la consulta.
        """

        normalized_limit = max(1, min(limit, 1_000))

        statement = (
            select(KnowledgeChunkModel)
            .where(
                KnowledgeChunkModel.embedding.is_(None),
            )
            .order_by(KnowledgeChunkModel.id)
            .limit(normalized_limit)
        )

        try:
            models = self._db.scalars(statement).all()

        except SQLAlchemyError as exc:
            raise KnowledgeServiceError(
                "No fue posible consultar los fragmentos pendientes"
            ) from exc

        return [
            self._to_chunk(
                model=model,
                score=None,
            )
            for model in models
        ]

    async def save_embeddings(
        self,
        embeddings: list[KnowledgeChunkEmbedding],
    ) -> None:
        """
        Guarda embeddings sobre fragmentos existentes.

        Esta operación actualiza registros ya creados en `kb_chunks`. No crea
        nuevos fragmentos ni duplica contenido.

        La escritura se ejecuta dentro de una transacción. Si alguno de los
        fragmentos no existe, si hay IDs repetidos o si ocurre un error de base
        de datos, se revierte toda la operación para evitar una indexación
        parcial.

        Args:
            embeddings: Lista de asociaciones entre ID de fragmento y vector.

        Returns:
            None.

        Raises:
            KnowledgeServiceError: Si hay fragmentos duplicados en la entrada.
            KnowledgeServiceError: Si algún embedding está vacío.
            KnowledgeServiceError: Si algún embedding no coincide con la
                dimensión configurada.
            KnowledgeServiceError: Si alguno de los fragmentos no existe.
            KnowledgeServiceError: Si PostgreSQL no puede guardar los
                embeddings.
        """

        if not embeddings:
            return

        chunk_ids = [item.chunk_id for item in embeddings]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise KnowledgeServiceError(
                "No se permiten fragmentos duplicados al guardar embeddings"
            )

        for item in embeddings:
            self._validate_embedding(list(item.embedding))

        try:
            for item in embeddings:
                statement = (
                    update(KnowledgeChunkModel)
                    .where(
                        KnowledgeChunkModel.id == item.chunk_id,
                    )
                    .values(
                        embedding=list(item.embedding),
                    )
                )

                result = cast(
                    CursorResult[Any],
                    self._db.execute(statement),
                )

                if result.rowcount != 1:
                    raise KnowledgeServiceError(f"No existe el fragmento {item.chunk_id}")

            self._db.commit()

        except KnowledgeServiceError:
            self._db.rollback()
            raise

        except SQLAlchemyError as exc:
            self._db.rollback()

            raise KnowledgeServiceError("No fue posible guardar los embeddings") from exc

        logger.info(
            "Embeddings saved count=%s",
            len(embeddings),
        )

    def _validate_embedding(
        self,
        embedding: list[float],
    ) -> None:
        """
        Valida que un embedding sea utilizable por pgvector.

        La dimensión del vector debe coincidir con la dimensión configurada para
        el modelo de embeddings. Esto evita errores al consultar o persistir en
        una columna vectorial con tamaño fijo.

        Args:
            embedding: Vector que será consultado o persistido.

        Raises:
            KnowledgeServiceError: Si el embedding está vacío.
            KnowledgeServiceError: Si el embedding no coincide con la dimensión
                configurada.
        """

        if not embedding:
            raise KnowledgeServiceError("El embedding no puede estar vacío")

        if len(embedding) != self._dimensions:
            raise KnowledgeServiceError("El embedding no coincide con la dimensión configurada")

    @staticmethod
    def _to_chunk(
        model: KnowledgeChunkModel,
        score: float | None,
    ) -> KnowledgeChunk:
        """
        Convierte un modelo ORM en un objeto de valor del dominio.

        Esta conversión evita que la capa de aplicación trabaje directamente con
        modelos SQLAlchemy. El resultado es un `KnowledgeChunk`, que representa
        un fragmento seguro y desacoplado de la infraestructura.

        Args:
            model: Modelo ORM obtenido desde la tabla `kb_chunks`.
            score: Puntaje de similitud calculado durante la búsqueda. Puede ser
                None cuando el fragmento no proviene de una búsqueda semántica.

        Returns:
            Objeto de valor `KnowledgeChunk`.
        """

        return KnowledgeChunk(
            id=model.id,
            text=model.content,
            source=model.source,
            title=model.title,
            metadata=dict(model.chunk_metadata),
            score=score,
        )
