"""
Puerto para proveedores de modelos de lenguaje.

Este módulo define el contrato que debe cumplir cualquier proveedor encargado
de generar respuestas del agente conversacional a partir de una solicitud
normalizada.

El uso de DTOs permite desacoplar la lógica de aplicación del proveedor
concreto de IA, como OpenAI, Azure OpenAI, un modelo local o una
implementación simulada para pruebas.
"""

from typing import Protocol

from app.application.dtos import LLMRequestDTO, LLMResponseDTO


class LLMProvider(Protocol):
    """
    Contrato para servicios de generación de lenguaje.

    Representa un puerto de salida de la aplicación. Las implementaciones
    concretas deben recibir una solicitud normalizada y retornar una respuesta
    también normalizada, evitando que el resto del sistema dependa de detalles
    específicos del proveedor de IA.
    """

    async def complete(
        self,
        request: LLMRequestDTO,
    ) -> LLMResponseDTO:
        """
        Genera una respuesta mediante un modelo de lenguaje.

        Args:
            request: Solicitud normalizada con la información necesaria para
                generar la respuesta, como historial conversacional, contexto,
                instrucciones del sistema o metadata requerida por el agente.

        Returns:
            LLMResponseDTO: Respuesta normalizada generada por el proveedor de IA.
        """
        ...
