"""
Puerto para proveedores de embeddings.

Este módulo define el contrato que debe cumplir cualquier proveedor encargado de
convertir textos en vectores semánticos.

La capa de aplicación depende de este puerto y no de una implementación concreta
como OpenAI, Azure OpenAI, Bedrock u otro servicio externo. Esto permite cambiar
el proveedor de embeddings sin modificar los servicios, herramientas o casos de
uso que consumen este contrato.

Responsabilidades del puerto:
    - Recibir una lista de textos.
    - Generar un vector semántico por cada texto.
    - Mantener el mismo orden entre la entrada y la salida.
    - Ocultar los detalles concretos del proveedor externo.
"""

from typing import Protocol


class EmbeddingProvider(Protocol):
    """
    Contrato para convertir textos en vectores semánticos.

    Un proveedor de embeddings transforma texto plano en representaciones
    numéricas. Estos vectores pueden utilizarse para búsquedas semánticas,
    recuperación de contexto, comparación de similitud o flujos RAG.

    Las implementaciones concretas pueden usar distintos proveedores externos,
    pero deben respetar la misma interfaz para que la aplicación no dependa de
    detalles específicos de infraestructura.

    Examples:
        Una implementación concreta podría usar OpenAI:

            provider = OpenAIEmbeddingProvider(...)
            vectors = await provider.embed(["texto uno", "texto dos"])

        El resultado debe conservar el orden:

            vectors[0] corresponde a "texto uno"
            vectors[1] corresponde a "texto dos"
    """

    async def embed(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Genera un embedding por cada texto recibido.

        La implementación debe conservar el orden exacto de los textos de
        entrada. Esto es importante porque los servicios que consumen este
        puerto suelen asociar cada vector con el texto ubicado en la misma
        posición.

        Args:
            texts: Lista de textos que serán convertidos en vectores
                semánticos.

        Returns:
            Lista de embeddings en el mismo orden de entrada. Cada embedding es
            una lista de números flotantes.

        Raises:
            EmbeddingProviderError: Si la implementación concreta no puede
                comunicarse con el proveedor externo o no puede generar los
                embeddings. Esta excepción depende de la implementación concreta.
        """

        ...
