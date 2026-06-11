"""
Herramienta para consultar la base de conocimiento mediante RAG.

Este módulo define la herramienta que permite al agente buscar información
oficial en la base de conocimiento de la tienda.

La herramienta usa un servicio de recuperación semántica para encontrar
fragmentos relevantes y devolverlos en un formato seguro para el agente. Estos
fragmentos pueden provenir de políticas internas, preguntas frecuentes,
procedimientos de soporte, reglas de garantía, devoluciones, envíos o guías de
solución de problemas.

Flujo general:
    1. El agente envía una consulta concreta.
    2. El DTO de entrada valida y normaliza los argumentos.
    3. `RetrievalService` genera el embedding de la consulta.
    4. El servicio busca fragmentos similares en el vector store.
    5. La herramienta convierte los fragmentos recuperados en DTOs seguros.
    6. El agente usa esos fragmentos como contexto para responder.

Regla importante:
    La respuesta final del agente debe basarse únicamente en los fragmentos
    retornados por esta herramienta cuando esté resolviendo preguntas que
    requieren información oficial de la base de conocimiento.

Este módulo pertenece a la capa de aplicación. No conoce detalles de OpenAI,
pgvector, SQLAlchemy ni PostgreSQL directamente.
"""

from app.application.dtos.knowledge import (
    KnowledgeChunkResultDTO,
    KnowledgeSearchInputDTO,
    KnowledgeSearchResultDTO,
)
from app.application.exceptions import KnowledgeServiceError
from app.application.services.retrieval_service import RetrievalService
from app.application.tools.base import Tool
from app.domain.value_objects import KnowledgeChunk


def knowledge_chunk_to_result_dto(
    chunk: KnowledgeChunk,
) -> KnowledgeChunkResultDTO:
    """
    Convierte un fragmento recuperado en un DTO seguro.

    Esta función transforma un objeto de valor del dominio en una estructura de
    salida apta para el agente. El DTO resultante contiene únicamente la
    información necesaria para construir una respuesta basada en contexto:
    fuente, título, contenido, metadatos y score de similitud.

    El `score` es obligatorio porque permite saber qué tan relevante fue el
    fragmento frente a la consulta semántica realizada. Si el fragmento no tiene
    score, significa que no proviene de una búsqueda válida para este flujo.

    Args:
        chunk: Fragmento recuperado desde la base de conocimiento.

    Returns:
        DTO seguro con la información del fragmento.

    Raises:
        KnowledgeServiceError: Si el fragmento no contiene score de similitud.
    """

    if chunk.score is None:
        raise KnowledgeServiceError("El fragmento recuperado no contiene un score de similitud")

    return KnowledgeChunkResultDTO(
        source=chunk.source,
        title=chunk.title,
        content=chunk.text,
        metadata=dict(chunk.metadata),
        score=chunk.score,
    )


class SearchKnowledgeBaseTool(
    Tool[
        KnowledgeSearchInputDTO,
        KnowledgeSearchResultDTO,
    ]
):
    """
    Herramienta para consultar políticas y procedimientos internos.

    Esta herramienta permite que el agente busque información oficial dentro de
    la base de conocimiento antes de responder preguntas que no deberían
    resolverse por memoria del modelo.

    Debe usarse para preguntas relacionadas con:

        - Garantías.
        - Exclusiones de garantía.
        - Devoluciones.
        - Envíos.
        - Procedimientos de soporte.
        - Solución de problemas.
        - Políticas internas de atención al cliente.

    La herramienta no genera la respuesta final al usuario. Su responsabilidad
    es recuperar fragmentos relevantes y entregarlos al agente en una estructura
    validada.

    Attributes:
        _retrieval_service: Servicio encargado de ejecutar la recuperación
            semántica.
    """

    name = "search_knowledge_base"

    description = (
        "Busca información oficial en la base de conocimiento de la tienda. "
        "Úsala para responder preguntas sobre garantías, exclusiones, "
        "devoluciones, envíos, procedimientos de soporte y solución de "
        "problemas. La respuesta debe basarse únicamente en los fragmentos "
        "retornados y debe mencionar la fuente cuando sea útil."
    )

    def __init__(
        self,
        retrieval_service: RetrievalService,
    ) -> None:
        """
        Inicializa la herramienta de búsqueda en la base de conocimiento.

        Args:
            retrieval_service: Servicio de recuperación semántica usado para
                buscar fragmentos relevantes.
        """

        self._retrieval_service = retrieval_service

    @property
    def input_model(self) -> type[KnowledgeSearchInputDTO]:
        """
        Retorna el DTO usado para validar los argumentos de entrada.

        Este modelo define la estructura que debe enviar el agente al invocar la
        herramienta. También normaliza la consulta y restringe campos
        inesperados.

        Returns:
            Clase DTO usada para validar la entrada de la herramienta.
        """

        return KnowledgeSearchInputDTO

    async def execute(
        self,
        arguments: KnowledgeSearchInputDTO,
    ) -> KnowledgeSearchResultDTO:
        """
        Ejecuta la búsqueda semántica en la base de conocimiento.

        Usa la consulta y el límite indicados en `arguments` para recuperar
        fragmentos relevantes mediante `RetrievalService`.

        Luego convierte cada fragmento recuperado en un DTO seguro y construye
        un resultado consistente para el agente.

        Args:
            arguments: Entrada validada con la consulta y el límite de
                fragmentos solicitados.

        Returns:
            Resultado estructurado de la búsqueda semántica. Incluye si la
            operación fue exitosa, si encontró fragmentos, la cantidad de
            resultados y la lista de fragmentos recuperados.

        Raises:
            KnowledgeServiceError: Si algún fragmento recuperado no contiene
                score de similitud.
            KnowledgeServiceError: Si el servicio de recuperación falla al
                generar embeddings o buscar en el vector store.
        """

        chunks = await self._retrieval_service.retrieve(
            query=arguments.query,
            limit=arguments.limit,
        )

        results = [knowledge_chunk_to_result_dto(chunk) for chunk in chunks]

        return KnowledgeSearchResultDTO(
            success=True,
            found=bool(results),
            count=len(results),
            chunks=results,
        )
