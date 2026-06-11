"""
Adaptador de OpenAI para generación de respuestas y uso de herramientas.

Este módulo implementa el proveedor concreto de lenguaje usando OpenAI
Responses API. Su responsabilidad es adaptar los DTOs internos de la
aplicación al formato requerido por OpenAI y normalizar la respuesta del
proveedor para que el resto del sistema no dependa directamente del SDK.

El adaptador soporta:
- Envío de historial conversacional.
- Exposición de herramientas como funciones.
- Continuación de respuestas usando resultados de herramientas.
- Extracción de tool calls generados por el modelo.
- Normalización de métricas de tokens.
- Conversión de esquemas Pydantic al modo estricto requerido por OpenAI.
"""

import json
import logging
from copy import deepcopy
from typing import Any

from openai import AsyncOpenAI, OpenAIError
from openai.types.responses import (
    EasyInputMessageParam,
    FunctionToolParam,
    ResponseFunctionToolCall,
    ResponseInputParam,
    ResponseTextConfigParam,
)
from openai.types.responses.response_input_param import FunctionCallOutput
from openai.types.shared_params import Reasoning

from app.application.dtos import (
    ChatMessageDTO,
    LLMRequestDTO,
    LLMResponseDTO,
    MessageRole,
    ToolCallDTO,
    ToolDefinitionDTO,
    ToolResultDTO,
)
from app.application.exceptions import LLMServiceError
from app.infrastructure.config import Settings, get_settings

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """
    Proveedor de lenguaje basado en OpenAI Responses API.

    Esta clase actúa como adaptador entre la capa de aplicación y OpenAI.
    Recibe solicitudes normalizadas, construye la petición compatible con
    Responses API y retorna una respuesta también normalizada.

    La infraestructura queda encapsulada en esta clase para evitar que tipos,
    errores o detalles del SDK de OpenAI se propaguen hacia el dominio o los
    servicios de aplicación.
    """

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        """
        Inicializa el cliente asíncrono de OpenAI.

        Args:
            settings: Configuración opcional de la aplicación. Si no se recibe,
                se carga desde variables de entorno mediante `get_settings`.

        Raises:
            ValueError: Si `OPENAI_API_KEY` no está configurada.
        """
        self._settings = settings or get_settings()

        if not self._settings.openai_api_key:
            raise ValueError("La variable OPENAI_API_KEY no está configurada")

        self._client = AsyncOpenAI(
            api_key=self._settings.openai_api_key,
            timeout=self._settings.openai_timeout_seconds,
            max_retries=self._settings.openai_max_retries,
        )
        self._model = self._settings.openai_model

    async def complete(
        self,
        request: LLMRequestDTO,
    ) -> LLMResponseDTO:
        """
        Genera una respuesta o solicitudes de herramientas mediante OpenAI.

        Cuando la solicitud no contiene resultados de herramientas, se envía el
        historial conversacional completo junto con las herramientas disponibles.
        Cuando existen resultados de herramientas, se envían esos resultados
        vinculados a la respuesta anterior mediante `previous_response_id`.

        Args:
            request: Solicitud normalizada con instrucciones del sistema,
                mensajes, herramientas disponibles, resultados de herramientas
                y posible identificador de respuesta previa.

        Returns:
            LLMResponseDTO: Respuesta normalizada con texto generado, llamadas
            de herramientas, identificador de respuesta, modelo usado y métricas
            de tokens.

        Raises:
            LLMServiceError: Si OpenAI falla, retorna una respuesta inválida o
                no produce ni texto ni llamadas de herramientas.
        """
        input_items = self._build_input(request)
        tools = [self._to_openai_tool(tool) for tool in request.tools]

        reasoning: Reasoning = {
            "effort": self._settings.openai_reasoning_effort,
        }
        text: ResponseTextConfigParam = {
            "verbosity": self._settings.openai_verbosity,
        }

        logger.info(
            "Sending OpenAI request model=%s tools=%s tool_results=%s previous_response_id=%s",
            self._model,
            len(tools),
            len(request.tool_results),
            request.previous_response_id,
        )

        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=request.instructions,
                input=input_items,
                tools=tools,
                previous_response_id=request.previous_response_id,
                parallel_tool_calls=True,
                reasoning=reasoning,
                text=text,
                max_output_tokens=self._settings.openai_max_output_tokens,
                store=True,
                stream=False,
            )
        except OpenAIError as exc:
            logger.exception(
                "OpenAI request failed model=%s",
                self._model,
            )
            raise LLMServiceError("No fue posible obtener respuesta del modelo") from exc

        tool_calls = self._extract_tool_calls(response.output)
        content = response.output_text.strip() or None

        if content is None and not tool_calls:
            raise LLMServiceError("OpenAI devolvió una respuesta sin texto ni herramientas")

        usage = response.usage
        input_tokens = usage.input_tokens if usage else 0
        output_tokens = usage.output_tokens if usage else 0
        reasoning_tokens = 0

        if usage and usage.output_tokens_details:
            reasoning_tokens = usage.output_tokens_details.reasoning_tokens or 0

        logger.info(
            "OpenAI request completed response_id=%s "
            "tool_calls=%s input_tokens=%s output_tokens=%s "
            "reasoning_tokens=%s",
            response.id,
            len(tool_calls),
            input_tokens,
            output_tokens,
            reasoning_tokens,
        )

        return LLMResponseDTO(
            content=content,
            tool_calls=tool_calls,
            response_id=response.id,
            model=response.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
        )

    def _build_input(
        self,
        request: LLMRequestDTO,
    ) -> ResponseInputParam:
        """
        Construye la entrada enviada a OpenAI Responses API.

        Si la solicitud contiene resultados de herramientas, se envían
        únicamente esos resultados. El historial previo queda asociado mediante
        `previous_response_id`. Si no hay resultados de herramientas, se envía
        el historial conversacional normal.

        Args:
            request: Solicitud normalizada de la aplicación.

        Returns:
            ResponseInputParam: Entrada compatible con Responses API.
        """
        if request.tool_results:
            return [self._to_openai_tool_result(result) for result in request.tool_results]

        return [self._to_openai_message(message) for message in request.messages]

    @staticmethod
    def _to_openai_message(
        message: ChatMessageDTO,
    ) -> EasyInputMessageParam:
        """
        Convierte un mensaje interno al formato de mensaje aceptado por OpenAI.

        Args:
            message: Mensaje almacenado en la conversación, con rol y contenido.

        Returns:
            EasyInputMessageParam: Mensaje compatible con Responses API.
        """
        if message.role is MessageRole.USER:
            return {
                "role": "user",
                "content": message.content,
            }

        return {
            "role": "assistant",
            "content": message.content,
        }

    @classmethod
    def _to_openai_tool(
        cls,
        tool: ToolDefinitionDTO,
    ) -> FunctionToolParam:
        """
        Convierte una definición interna de herramienta en una función de OpenAI.

        Args:
            tool: Definición de herramienta independiente del proveedor.

        Returns:
            FunctionToolParam: Herramienta compatible con Responses API en modo
            estricto.
        """
        return {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": cls._make_schema_strict(tool.parameters),
            "strict": True,
        }

    @staticmethod
    def _to_openai_tool_result(
        result: ToolResultDTO,
    ) -> FunctionCallOutput:
        """
        Convierte el resultado de una herramienta al formato esperado por OpenAI.

        El resultado se serializa como JSON y se vincula con el `call_id`
        generado por OpenAI para la llamada de herramienta original.

        Args:
            result: Resultado interno de una herramienta ejecutada.

        Returns:
            FunctionCallOutput: Resultado compatible con Responses API.
        """
        return {
            "type": "function_call_output",
            "call_id": result.call_id,
            "output": json.dumps(
                result.output,
                ensure_ascii=False,
            ),
        }

    @staticmethod
    def _extract_tool_calls(
        output: list[Any],
    ) -> list[ToolCallDTO]:
        """
        Extrae y normaliza las llamadas de herramientas generadas por OpenAI.

        Args:
            output: Lista de elementos retornados por Responses API.

        Returns:
            list[ToolCallDTO]: Llamadas de herramientas normalizadas para la
            capa de aplicación.

        Raises:
            LLMServiceError: Si los argumentos generados por OpenAI no son JSON
                válido o no representan un objeto.
        """
        tool_calls: list[ToolCallDTO] = []

        for item in output:
            if not isinstance(item, ResponseFunctionToolCall):
                continue

            try:
                arguments = json.loads(item.arguments)
            except json.JSONDecodeError as exc:
                raise LLMServiceError(
                    f"OpenAI generó argumentos inválidos para '{item.name}'"
                ) from exc

            if not isinstance(arguments, dict):
                raise LLMServiceError(f"OpenAI generó argumentos no válidos para '{item.name}'")

            tool_calls.append(
                ToolCallDTO(
                    call_id=item.call_id,
                    name=item.name,
                    arguments=arguments,
                )
            )

        return tool_calls

    @classmethod
    def _make_schema_strict(
        cls,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Adapta un JSON Schema de Pydantic al modo estricto de OpenAI.

        OpenAI requiere que los objetos no admitan propiedades adicionales y
        que todas sus propiedades estén listadas en `required`. Los campos
        opcionales siguen admitiendo `null` si así fueron definidos por
        Pydantic.

        Args:
            schema: Esquema JSON generado por un modelo Pydantic.

        Returns:
            dict[str, Any]: Copia del esquema adaptada para uso estricto en
            OpenAI.
        """
        strict_schema = deepcopy(schema)
        cls._apply_strict_rules(strict_schema)

        return strict_schema

    @classmethod
    def _apply_strict_rules(
        cls,
        node: Any,
    ) -> None:
        """
        Aplica reglas estrictas de OpenAI sobre un nodo del JSON Schema.

        La transformación se realiza de forma recursiva sobre diccionarios y
        listas para cubrir objetos anidados, arrays y definiciones internas del
        esquema.

        Args:
            node: Nodo actual del JSON Schema que será inspeccionado y, si
                aplica, modificado.
        """
        if isinstance(node, dict):
            properties = node.get("properties")

            if isinstance(properties, dict):
                node["additionalProperties"] = False
                node["required"] = list(properties)

            for value in node.values():
                cls._apply_strict_rules(value)

        elif isinstance(node, list):
            for item in node:
                cls._apply_strict_rules(item)
