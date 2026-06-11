"""
Adaptador OpenAI para generación de embeddings.

Este módulo implementa el puerto `EmbeddingProvider` usando el SDK asíncrono de
OpenAI.

Su responsabilidad es convertir textos planos en vectores semánticos que luego
pueden usarse para búsqueda vectorial, recuperación de contexto, comparación de
similitud o flujos RAG..

Responsabilidades del adaptador:
    - Leer la configuración necesaria para conectarse a OpenAI.
    - Validar que exista una API key configurada.
    - Normalizar los textos antes de enviarlos al proveedor.
    - Solicitar embeddings de forma asíncrona.
    - Conservar el orden de los textos de entrada.
    - Validar que la respuesta del proveedor sea consistente.
    - Traducir errores del SDK a excepciones propias de la aplicación.
"""

import logging

from openai import AsyncOpenAI, OpenAIError

from app.application.exceptions import KnowledgeServiceError
from app.application.ports.embedding_provider import EmbeddingProvider
from app.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    Adaptador de embeddings basado en OpenAI.

    Esta clase implementa el contrato `EmbeddingProvider` y encapsula todos los
    detalles específicos del SDK de OpenAI. El resto de la aplicación solo
    conoce el métod `embed`, definido por el puerto.

    La configuración se obtiene desde `Settings`, incluyendo:

        - API key de OpenAI.
        - Tiempo máximo de espera.
        - Cantidad máxima de reintentos.
        - Modelo de embeddings.
        - Dimensión esperada del vector.

    Attributes:
        _settings: Configuración de infraestructura usada por el adaptador.
        _client: Cliente asíncrono de OpenAI.
        _model: Modelo de embeddings configurado.
        _dimensions: Dimensión esperada para cada embedding generado.

    Raises:
        ValueError: Si `OPENAI_API_KEY` no está configurada.
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        """
        Inicializa el proveedor de embeddings de OpenAI.

        Si no se recibe una configuración explícita, se carga la configuración
        global mediante `get_settings`.

        Args:
            settings: Configuración opcional de la aplicación. Se usa
                principalmente para pruebas o para inyectar configuración
                controlada.

        Raises:
            ValueError: Si la API key de OpenAI no está configurada.
        """

        self._settings = settings or get_settings()

        if not self._settings.openai_api_key:
            raise ValueError("La variable OPENAI_API_KEY no está configurada")

        self._client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
            max_retries=self._settings.openai_max_retries,
        )

        self._model = self._settings.embedding_model
        self._dimensions = self._settings.embedding_dimensions

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Genera un embedding por cada texto recibido.

        Cada texto se normaliza antes de enviarse al proveedor. La normalización
        elimina espacios repetidos, saltos de línea y tabulaciones internas,
        conservando una única separación entre palabras.

        El métod conserva el orden lógico de entrada. Si OpenAI retorna los
        embeddings con índices, la respuesta se ordena usando `item.index` antes
        de construir la lista final.

        Args:
            texts: Lista de textos que serán convertidos en vectores
                semánticos.

        Returns:
            Lista de embeddings en el mismo orden de los textos recibidos. Cada
            embedding es una lista de números flotantes.

        Raises:
            KnowledgeServiceError: Si alguno de los textos queda vacío después
                de normalizarse.
            KnowledgeServiceError: Si OpenAI falla al generar los embeddings.
            KnowledgeServiceError: Si el proveedor retorna una cantidad de
                embeddings diferente a la esperada.
            KnowledgeServiceError: Si algún embedding tiene una dimensión
                diferente a la configurada.

        Notes:
            Si `texts` está vacío, retorna una lista vacía sin llamar a OpenAI.

            Este métod no persiste los embeddings. Solo los genera y retorna.
            El almacenamiento corresponde al repositorio o vector store que
            consuma este proveedor.
        """

        normalized_texts = [" ".join(text.split()) for text in texts]

        if not normalized_texts:
            return []

        if any(not text for text in normalized_texts):
            raise KnowledgeServiceError("No es posible generar embeddings para textos vacíos")

        logger.info(
            "Generating embeddings model=%s texts=%s dimensions=%s",
            self._model,
            len(normalized_texts),
            self._dimensions,
        )

        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=normalized_texts,
                encoding_format="float",
                dimensions=self._dimensions,
            )

        except OpenAIError as exc:
            logger.exception(
                "Embedding request failed model=%s",
                self._model,
            )

            raise KnowledgeServiceError("No fue posible generar los embeddings") from exc

        ordered_data = sorted(
            response.data,
            key=lambda item: item.index,
        )

        embeddings = [list(item.embedding) for item in ordered_data]

        if len(embeddings) != len(normalized_texts):
            raise KnowledgeServiceError("El proveedor retornó una cantidad inválida de embeddings")

        if any(len(vector) != self._dimensions for vector in embeddings):
            raise KnowledgeServiceError("El proveedor retornó embeddings con dimensión inválida")

        logger.info(
            "Embeddings generated model=%s count=%s",
            self._model,
            len(embeddings),
        )

        return embeddings
