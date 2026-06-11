"""
DTOs para la comunicación con proveedores de lenguaje.

Este módulo define modelos de transferencia de datos usados para enviar
solicitudes a un LLM, recibir respuestas normalizadas, declarar herramientas
disponibles y transportar resultados de herramientas ejecutadas por la
aplicación.

Los DTOs están diseñados para no depender de un proveedor específico como
OpenAI, Anthropic, Google u otro. De esta forma, la capa de aplicación puede
trabajar con una interfaz común sin acoplarse a una implementación concreta.
"""

from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.application.dtos.chat import ChatMessageDTO


class ToolDefinitionDTO(BaseModel):
    """
    Define una herramienta que puede ser utilizada por el modelo de lenguaje.

    Este DTO representa la definición pública de una herramienta disponible
    para el LLM. Incluye su nombre, una descripción funcional y el esquema
    JSON de parámetros que el modelo debe respetar al solicitar su ejecución.

    Attributes:
        name: Nombre único de la herramienta. Debe ser corto, legible y usar
            únicamente letras, números, guiones o guiones bajos.
        description: Descripción clara de la finalidad de la herramienta y
            cuándo debe ser utilizada por el modelo.
        parameters: Esquema JSON que describe los argumentos aceptados por la
            herramienta.
    """

    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    description: str = Field(
        min_length=1,
        max_length=2_000,
    )
    parameters: dict[str, Any]


class ToolCallDTO(BaseModel):
    """
    Representa una solicitud del modelo para ejecutar una herramienta.

    El LLM puede responder indicando que necesita usar una herramienta externa
    para completar la solicitud del usuario. Este DTO normaliza esa intención
    y permite que la aplicación ejecute la herramienta correspondiente.

    Attributes:
        call_id: Identificador único de la invocación. Se usa para asociar el
            resultado de la herramienta con la llamada original.
        name: Nombre de la herramienta que el modelo solicita ejecutar.
        arguments: Argumentos generados por el modelo para invocar la
            herramienta.
    """

    call_id: str = Field(
        min_length=1,
        max_length=200,
    )
    name: str = Field(
        min_length=1,
        max_length=64,
    )
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResultDTO(BaseModel):
    """
    Representa el resultado retornado por una herramienta ejecutada.

    Después de que la aplicación ejecuta una herramienta solicitada por el LLM,
    el resultado se encapsula en este DTO para enviarlo nuevamente al proveedor
    de lenguaje y continuar la generación de la respuesta.

    Attributes:
        call_id: Identificador de la llamada de herramienta que produjo este
            resultado. Debe coincidir con el `call_id` recibido en
            `ToolCallDTO`.
        output: Resultado serializable retornado por la herramienta.
    """

    call_id: str = Field(
        min_length=1,
        max_length=200,
    )
    output: dict[str, Any] = Field(default_factory=dict)


class LLMRequestDTO(BaseModel):
    """
    Representa una solicitud normalizada hacia un proveedor de lenguaje.

    Este DTO agrupa las instrucciones del agente, el historial conversacional,
    las herramientas disponibles y, cuando aplica, los resultados de
    herramientas ejecutadas previamente.

    Está diseñado para soportar tanto una primera solicitud al LLM como la
    continuación de una respuesta luego de ejecutar herramientas externas.

    Attributes:
        instructions: Instrucciones generales del sistema o del agente.
        messages: Historial conversacional que será enviado al modelo.
        tools: Lista de herramientas disponibles para que el modelo pueda
            solicitarlas cuando las necesite.
        tool_results: Resultados de herramientas previamente ejecutadas por la
            aplicación.
        previous_response_id: Identificador de una respuesta previa que debe
            continuarse. Es requerido cuando se envían resultados de
            herramientas.
    """

    instructions: str = Field(min_length=1)
    messages: list[ChatMessageDTO]
    tools: list[ToolDefinitionDTO] = Field(default_factory=list)
    tool_results: list[ToolResultDTO] = Field(default_factory=list)
    previous_response_id: str | None = None

    @model_validator(mode="after")
    def validate_tool_continuation(self) -> Self:
        """
        Valida que los resultados de herramientas continúen una respuesta previa.

        Cuando `tool_results` contiene información, significa que la aplicación
        ya ejecutó una o más herramientas solicitadas por el modelo. En ese caso,
        se necesita `previous_response_id` para indicar qué respuesta del LLM se
        está continuando.

        Returns:
            Self: Instancia validada de `LLMRequestDTO`.

        Raises:
            ValueError: Si se envían resultados de herramientas sin indicar
                `previous_response_id`.
        """
        if self.tool_results and self.previous_response_id is None:
            raise ValueError("Los resultados de herramientas requieren previous_response_id")

        return self


class LLMResponseDTO(BaseModel):
    """
    Representa una respuesta normalizada de un proveedor de lenguaje.

    Una respuesta del LLM puede contener texto final para el usuario,
    solicitudes de ejecución de herramientas, o ambas cosas. Este DTO permite
    que la aplicación procese la salida del modelo de forma uniforme,
    independientemente del proveedor utilizado.

    Attributes:
        content: Texto generado por el modelo para responder al usuario.
        tool_calls: Lista de herramientas que el modelo solicita ejecutar.
        response_id: Identificador de la respuesta generada por el proveedor.
            Puede usarse para continuar la conversación después de ejecutar
            herramientas.
        model: Nombre del modelo que produjo la respuesta.
        input_tokens: Cantidad de tokens recibidos por el modelo.
        output_tokens: Cantidad de tokens generados por el modelo.
        reasoning_tokens: Cantidad de tokens usados en razonamiento, cuando el
            proveedor expone esta métrica.
    """

    content: str | None = None
    tool_calls: list[ToolCallDTO] = Field(default_factory=list)
    response_id: str | None = None
    model: str | None = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

    @field_validator("content")
    @classmethod
    def normalize_content(
        cls,
        value: str | None,
    ) -> str | None:
        """
        Normaliza el texto generado por el modelo.

        Elimina espacios externos del contenido. Si después de limpiar el texto
        queda una cadena vacía, retorna `None` para evitar manejar respuestas
        aparentemente válidas pero sin contenido real.

        Args:
            value: Texto generado por el modelo, o `None`.

        Returns:
            str | None: Texto normalizado, o `None` si no hay contenido útil.
        """
        if value is None:
            return None

        normalized_value = value.strip()

        return normalized_value or None

    @model_validator(mode="after")
    def validate_output(self) -> Self:
        """
        Valida que la respuesta tenga contenido útil.

        Una respuesta del LLM se considera válida si contiene texto para el
        usuario, llamadas a herramientas, o ambas cosas. Si no contiene ninguna
        de las dos, la respuesta no puede ser procesada por la aplicación.

        Returns:
            Self: Instancia validada de `LLMResponseDTO`.

        Raises:
            ValueError: Si la respuesta no contiene texto ni llamadas a
                herramientas.
        """
        if self.content is None and not self.tool_calls:
            raise ValueError("La respuesta del LLM no contiene texto ni herramientas")

        return self
