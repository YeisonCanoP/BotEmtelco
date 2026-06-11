"""
DTOs para buscar información en la base de conocimiento.

Este módulo define los modelos de entrada y salida utilizados por la herramienta
o servicio encargado de consultar la base de conocimiento del agente.

La base de conocimiento puede contener políticas, preguntas frecuentes,
procedimientos de soporte, guías de troubleshooting u otra información textual
que el agente utiliza como contexto para responder al usuario.

Modelos definidos:
    - KnowledgeSearchInputDTO: entrada para realizar una búsqueda.
    - KnowledgeChunkResultDTO: fragmento seguro retornado como resultado.
    - KnowledgeSearchResultDTO: respuesta completa de la búsqueda.

"""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class KnowledgeSearchInputDTO(BaseModel):
    """
    Entrada para buscar información en la base de conocimiento.

    Este DTO representa los argumentos que recibe la herramienta o servicio de
    búsqueda semántica. El usuario formula una pregunta o necesidad concreta, y
    el sistema usa `query` para recuperar fragmentos relevantes desde la base de
    conocimiento.

    Attributes:
        query: Pregunta o consulta concreta que debe resolverse usando la base
            de conocimiento.
        limit: Cantidad máxima de fragmentos relevantes que se deben retornar.

    Notes:
        `extra="forbid"` impide recibir campos no declarados. Esto evita que el
        LLM envíe argumentos inesperados a la herramienta.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=3,
        max_length=1_000,
        description=("Pregunta concreta que debe resolverse usando la base de conocimiento."),
    )

    limit: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Cantidad máxima de fragmentos relevantes.",
    )

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        """
        Normaliza la consulta del usuario.

        Elimina espacios repetidos, saltos de línea innecesarios y tabulaciones
        internas, conservando una única separación entre palabras.

        Args:
            value: Consulta original recibida.

        Returns:
            Consulta normalizada.
        """

        return " ".join(value.split())


class KnowledgeChunkResultDTO(BaseModel):
    """
    Fragmento seguro retornado al agente.

    Representa un fragmento recuperado desde la base de conocimiento después de
    una búsqueda semántica. Este DTO expone únicamente la información necesaria
    para que el agente construya una respuesta basada en contexto.

    Attributes:
        source: Documento, archivo, política o fuente de origen del fragmento.
        title: Título descriptivo del fragmento recuperado.
        content: Texto del fragmento que puede usarse como contexto.
        metadata: Información adicional del fragmento, por ejemplo categoría,
            idioma, versión, sección o etiquetas internas.
        score: Puntaje de similitud semántica entre cero y uno.

    Notes:
        El campo `score` debe representar similitud, no distancia. Un valor más
        alto significa que el fragmento es más relevante para la consulta.
    """

    source: str = Field(
        min_length=1,
        max_length=255,
    )

    title: str = Field(
        min_length=1,
        max_length=255,
    )

    content: str = Field(
        min_length=1,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    score: float = Field(
        ge=0,
        le=1,
    )


class KnowledgeSearchResultDTO(BaseModel):
    """
    Resultado de una búsqueda semántica en la base de conocimiento.

    Agrupa el estado de la búsqueda y los fragmentos recuperados. Este DTO
    permite que el agente sepa si la búsqueda fue exitosa, si encontró contenido
    útil y cuántos fragmentos debe considerar para responder.

    Attributes:
        success: Indica si la búsqueda se ejecutó correctamente.
        found: Indica si se encontraron fragmentos relevantes.
        count: Cantidad de fragmentos retornados.
        chunks: Lista de fragmentos relevantes recuperados.

    Notes:
        La consistencia entre `found`, `count`, `success` y `chunks` se valida
        después de construir el modelo.
    """

    success: bool

    found: bool

    count: int = Field(
        ge=0,
    )

    chunks: list[KnowledgeChunkResultDTO] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        """
        Valida la consistencia interna del resultado.

        Reglas:
            - `count` debe coincidir con la cantidad real de fragmentos.
            - `found` debe indicar correctamente si existen fragmentos.
            - Una búsqueda fallida no puede retornar fragmentos.

        Returns:
            La instancia validada.

        Raises:
            ValueError: Si `count` no coincide con la cantidad de fragmentos.
            ValueError: Si `found` no refleja la existencia de fragmentos.
            ValueError: Si una búsqueda fallida retorna fragmentos.
        """

        if self.count != len(self.chunks):
            raise ValueError("count debe coincidir con la cantidad de fragmentos")

        if self.found != bool(self.chunks):
            raise ValueError("found debe indicar si existen fragmentos")

        if not self.success and self.chunks:
            raise ValueError("Una búsqueda fallida no puede retornar fragmentos")

        return self
