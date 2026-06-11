"""
Registro central de herramientas disponibles para el agente.

Este módulo permite registrar, consultar, describir y ejecutar herramientas
sin acoplar el servicio del agente a implementaciones concretas.

El registro actúa como un punto único de acceso para las herramientas que el
modelo puede invocar durante una conversación, como consultas de catálogo,
comparaciones de productos, pedidos, garantías o soporte.
"""

from typing import Any

from app.application.exceptions import (
    ToolNotFoundError,
    ToolRegistrationError,
)
from app.application.tools.base import Tool


class ToolRegistry:
    """
    Registro de herramientas ejecutables por el agente.

    Cada herramienta se almacena por nombre único. El registro permite obtener
    sus definiciones públicas para exponerlas al proveedor LLM y ejecutar una
    herramienta específica cuando el modelo solicita su uso.

    Attributes:
        _tools: Diccionario interno de herramientas registradas por nombre.
    """

    def __init__(
        self,
        tools: list[Tool[Any, Any]] | None = None,
    ) -> None:
        """
        Inicializa el registro de herramientas.

        Args:
            tools: Lista opcional de herramientas que deben registrarse al
                crear la instancia.
        """
        self._tools: dict[str, Tool[Any, Any]] = {}

        for tool in tools or []:
            self.register(tool)

    def register(
        self,
        tool: Tool[Any, Any],
    ) -> None:
        """
        Registra una herramienta en el catálogo disponible para el agente.

        El nombre de la herramienta se normaliza eliminando espacios al inicio
        y al final. No se permiten nombres vacíos ni nombres repetidos.

        Args:
            tool: Herramienta que se desea agregar al registro.

        Raises:
            ToolRegistrationError: Si el nombre de la herramienta está vacío
                o si ya existe una herramienta registrada con el mismo nombre.
        """
        normalized_name = tool.name.strip()

        if not normalized_name:
            raise ToolRegistrationError(tool.name)

        if normalized_name in self._tools:
            raise ToolRegistrationError(normalized_name)

        self._tools[normalized_name] = tool

    def get(
        self,
        name: str,
    ) -> Tool[Any, Any]:
        """
        Obtiene una herramienta registrada por nombre.

        Args:
            name: Nombre de la herramienta solicitada.

        Returns:
            Tool[Any, Any]: Herramienta registrada con ese nombre.

        Raises:
            ToolNotFoundError: Si no existe una herramienta registrada con el
                nombre solicitado.
        """
        normalized_name = name.strip()

        try:
            return self._tools[normalized_name]
        except KeyError as exc:
            raise ToolNotFoundError(normalized_name) from exc

    def definitions(self) -> list[dict[str, Any]]:
        """
        Retorna las definiciones públicas de todas las herramientas registradas.

        Cada definición incluye el nombre, la descripción y el esquema de
        parámetros de la herramienta. Esta información puede enviarse al
        proveedor LLM para que el modelo conozca qué herramientas existen y
        cómo debe invocarlas.

        Returns:
            list[dict[str, Any]]: Lista de definiciones serializables de las
                herramientas disponibles.
        """
        return [tool.definition() for tool in self._tools.values()]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Ejecuta una herramienta registrada.

        Busca la herramienta por nombre, valida sus argumentos mediante la clase
        base `Tool` y retorna el resultado serializable de su ejecución.

        Args:
            name: Nombre de la herramienta que se desea ejecutar.
            arguments: Argumentos enviados por el modelo para la herramienta.

        Returns:
            dict[str, Any]: Resultado serializable producido por la herramienta.

        Raises:
            ToolNotFoundError: Si la herramienta solicitada no está registrada.
            ToolArgumentsError: Si los argumentos no cumplen el esquema esperado
                por la herramienta.
        """
        tool = self.get(name)

        return await tool.run(arguments)

    @property
    def names(self) -> tuple[str, ...]:
        """
        Retorna los nombres de las herramientas registradas.

        Returns:
            tuple[str, ...]: Nombres disponibles en el orden en que fueron
                registrados.
        """
        return tuple(self._tools)
