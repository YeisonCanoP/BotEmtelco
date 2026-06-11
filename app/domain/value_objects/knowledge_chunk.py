"""
Objetos de valor utilizados por la base de conocimiento.

Este módulo define estructuras simples e inmutables para representar información
relacionada con la base de conocimiento del agente.

Clases principales:
    - KnowledgeChunk: representa un fragmento textual recuperado o persistible.
    - KnowledgeChunkEmbedding: representa el embedding asociado a un fragmento
      existente.

"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    """
    Fragmento almacenado o recuperado desde la base de conocimiento.

    Representa una unidad textual utilizada por el agente para consultar
    información de soporte, políticas, preguntas frecuentes, guías técnicas o
    cualquier otro contenido relevante para responder al usuario.

    Un fragmento puede venir directamente desde la tabla `kb_chunks` o puede
    existir temporalmente antes de ser persistido. Por eso el campo `id` permite
    None.

    El campo `score` se usa cuando el fragmento proviene de una búsqueda
    semántica. Representa la similitud o relevancia del fragmento frente a la
    consulta realizada. Cuando el fragmento todavía no ha pasado por una
    búsqueda, este valor puede permanecer en None.

    Attributes:
        id: Identificador del fragmento en PostgreSQL. Puede ser None antes de
            persistirse.
        text: Contenido textual del fragmento usado como contexto para el
            agente.
        source: Documento, archivo, sección o fuente de origen del fragmento.
        title: Título descriptivo del fragmento.
        metadata: Metadatos adicionales del fragmento, por ejemplo categoría,
            idioma, versión, tipo de documento o etiquetas internas.
        score: Puntaje de similitud semántica entre cero y uno. Puede ser None
            cuando el fragmento no proviene de una búsqueda semántica.

    Notes:
        Esta clase es inmutable porque representa un valor del dominio. Si se
        necesita modificar algún campo, debe crearse una nueva instancia.
    """

    id: int | None
    text: str
    source: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeChunkEmbedding:
    """
    Embedding generado para un fragmento existente.

    Representa la asociación entre un fragmento ya persistido en la base de
    conocimiento y el vector numérico generado por un proveedor de embeddings.

    Esta clase se usa normalmente después de crear o actualizar fragmentos en
    `kb_chunks`, cuando el sistema necesita guardar su representación vectorial
    para búsquedas semánticas con pgvector u otro mecanismo equivalente.

    Attributes:
        chunk_id: Identificador del registro existente en `kb_chunks`.
        embedding: Vector generado por el proveedor de embeddings.

    Raises:
        ValueError: Si `chunk_id` no es mayor que cero.
        ValueError: Si `embedding` está vacío.

    Notes:
        El vector se modela como tupla para mantener inmutabilidad. Esto evita
        modificaciones accidentales después de crear el objeto de valor.
    """

    chunk_id: int
    embedding: tuple[float, ...]

    def __post_init__(self) -> None:
        """
        Valida que el identificador y el vector sean utilizables.

        La validación se ejecuta automáticamente después de crear la instancia,
        incluso al tratarse de un dataclass congelado.

        Raises:
            ValueError: Si `chunk_id` es menor que uno.
            ValueError: Si `embedding` no contiene valores.
        """

        if self.chunk_id < 1:
            raise ValueError("chunk_id debe ser mayor que cero")

        if not self.embedding:
            raise ValueError("embedding no puede estar vacío")
