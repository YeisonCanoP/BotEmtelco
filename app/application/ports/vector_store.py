"""
Puerto para almacenamiento y búsqueda vectorial.

Este módulo define el contrato que debe cumplir cualquier implementación
encargada de consultar, listar y actualizar fragmentos dentro de una base de
conocimiento vectorial.

La capa de aplicación depende de este puerto, no de una tecnología concreta como
pgvector, Pinecone, Chroma, Weaviate u otro motor vectorial. Esto permite
cambiar la infraestructura de búsqueda semántica sin modificar los servicios o
herramientas que usan este contrato.

Responsabilidades del puerto:
    - Buscar fragmentos similares a partir de un embedding de consulta.
    - Listar fragmentos que todavía no tienen embedding generado.
    - Guardar embeddings para fragmentos ya existentes.
    - Mantener separada la lógica de aplicación de los detalles de persistencia.

"""

from typing import Protocol

from app.domain.value_objects import (
    KnowledgeChunk,
    KnowledgeChunkEmbedding,
)


class VectorStore(Protocol):
    """
    Contrato para consultar y actualizar la base de conocimiento vectorial.

    Un `VectorStore` representa una abstracción sobre el mecanismo usado para
    realizar búsquedas semánticas y administrar embeddings asociados a
    fragmentos de conocimiento.

    La aplicación usa este contrato para trabajar con objetos de dominio como
    `KnowledgeChunk` y `KnowledgeChunkEmbedding`, sin conocer cómo se almacenan
    realmente los vectores.

    Ejemplos de implementaciones posibles:
        - PostgreSQL con pgvector.
        - Un motor vectorial externo.
        - Una implementación en memoria para pruebas.
        - Un mock para pruebas unitarias.

    """

    async def search(
        self,
        embedding: list[float],
        limit: int,
    ) -> list[KnowledgeChunk]:
        """
        Busca fragmentos similares al embedding recibido.

        Este métod recibe el vector semántico de una consulta y retorna los
        fragmentos más relacionados dentro de la base de conocimiento.

        El resultado debe estar ordenado de mayor a menor similitud. Cada
        fragmento retornado puede incluir un `score` que indique qué tan cercano
        es frente al embedding consultado.

        Escala esperada del score:
            - 1.0: máxima similitud.
            - 0.0: mínima similitud.

        Args:
            embedding: Vector semántico de la consulta.
            limit: Cantidad máxima de fragmentos que deben retornarse.

        Returns:
            Lista de fragmentos ordenados de mayor a menor similitud.
        """

        ...

    async def list_without_embeddings(
        self,
        limit: int = 100,
    ) -> list[KnowledgeChunk]:
        """
        Lista fragmentos que todavía no tienen embedding generado.

        Este métod se usa normalmente en procesos de indexación o
        sincronización de la base de conocimiento. Permite identificar registros
        existentes en `kb_chunks` cuyo campo de embedding todavía está vacío o
        nulo.

        Args:
            limit: Cantidad máxima de fragmentos pendientes que deben
                retornarse. Por defecto retorna hasta 100 registros.

        Returns:
            Lista de fragmentos pendientes de vectorización.
        """

        ...

    async def save_embeddings(
        self,
        embeddings: list[KnowledgeChunkEmbedding],
    ) -> None:
        """
        Guarda embeddings para fragmentos existentes.

        Este métod actualiza registros ya creados en la base de conocimiento,
        asociando cada `chunk_id` con su vector semántico correspondiente.

        No debe crear nuevos fragmentos ni duplicar contenido. Su responsabilidad
        se limita a persistir embeddings sobre registros existentes.

        Args:
            embeddings: Lista de asociaciones entre ID de fragmento y vector
                generado.

        Returns:
            None.
        """

        ...
