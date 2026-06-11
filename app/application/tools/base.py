"""
Abstracción base para herramientas ejecutables por el agente.

Este módulo define el contrato común que deben implementar las herramientas
de catálogo, clientes, pedidos, garantías y conocimiento.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ValidationError

from app.application.exceptions import ToolArgumentsError


class Tool[InputDTO: BaseModel, OutputDTO: BaseModel](ABC):
    """
    Contrato genérico para una herramienta del agente.

    Cada herramienta declara su nombre, descripción, modelo de entrada y
    operación concreta. La clase base se encarga de validar los argumentos
    antes de ejecutar la lógica de negocio.
    """

    name: str
    description: str

    @property
    @abstractmethod
    def input_model(self) -> type[InputDTO]:
        """
        Retorna el modelo Pydantic usado para validar los argumentos.

        Returns:
            type[InputDTO]: Clase del DTO de entrada.
        """
        raise NotImplementedError

    def definition(self) -> dict[str, Any]:
        """
        Construye la definición pública de la herramienta.

        La definición contiene la información que posteriormente será enviada
        al proveedor LLM para que el modelo conozca cuándo y cómo invocarla.

        Returns:
            dict[str, Any]: Nombre, descripción y esquema de argumentos.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_model.model_json_schema(),
        }

    async def run(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Valida argumentos, ejecuta la herramienta y serializa el resultado.

        Args:
            arguments: Argumentos sin validar solicitados por el modelo.

        Returns:
            dict[str, Any]: Resultado serializable de la herramienta.

        Raises:
            ToolArgumentsError: Si los argumentos no cumplen el modelo de entrada.
        """
        try:
            validated_arguments = self.input_model.model_validate(arguments)
        except ValidationError as exc:
            raise ToolArgumentsError(
                tool_name=self.name,
                details=str(exc),
            ) from exc

        result = await self.execute(validated_arguments)

        return result.model_dump(mode="json")

    @abstractmethod
    async def execute(
        self,
        arguments: InputDTO,
    ) -> OutputDTO:
        """
        Ejecuta la lógica específica de la herramienta.

        Args:
            arguments: Argumentos previamente validados.

        Returns:
            OutputDTO: Resultado normalizado de la herramienta.
        """
        raise NotImplementedError
