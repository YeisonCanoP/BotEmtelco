"""
Excepciones controladas de la capa de aplicación.

Este módulo define los errores esperados durante la ejecución de casos de uso,
proveedores externos, almacenamiento de sesiones y herramientas del agente.

Todas las excepciones heredan de `ApplicationError` para permitir un manejo
centralizado desde la capa de interfaces, sin exponer detalles internos de
infraestructura al cliente HTTP.
"""


class ApplicationError(Exception):
    """
    Excepción base de la capa de aplicación.

    Debe ser usada como clase padre para errores controlados del sistema.
    """


class LLMServiceError(ApplicationError):
    """
    Error producido durante la comunicación con el modelo de lenguaje.

    Se utiliza cuando el proveedor LLM falla, retorna una respuesta inválida
    o no puede completar la solicitud del agente.
    """


class SessionStoreError(ApplicationError):
    """
    Error producido al consultar o guardar una conversación.

    Se utiliza cuando el almacenamiento de sesiones no está disponible,
    falla la lectura, falla la escritura o el contenido persistido no es válido.
    """


class ToolError(ApplicationError):
    """
    Excepción base para errores relacionados con herramientas.

    Agrupa errores esperados durante el registro, búsqueda, validación o
    ejecución de herramientas disponibles para el agente.
    """


class ToolRegistrationError(ToolError):
    """
    Error producido al registrar una herramienta.

    Se utiliza cuando una herramienta no puede ser registrada, por ejemplo
    porque su nombre ya existe o porque su definición no es válida.
    """

    def __init__(self, tool_name: str) -> None:
        """
        Inicializa el error de registro de herramienta.

        Args:
            tool_name: Nombre de la herramienta duplicada o inválida.
        """
        self.tool_name = tool_name

        super().__init__(f"No fue posible registrar la herramienta '{tool_name}'")


class ToolNotFoundError(ToolError):
    """
    Error producido cuando una herramienta solicitada no está registrada.

    Se utiliza cuando el agente o el proveedor LLM intenta invocar una
    herramienta que no existe dentro del registro disponible.
    """

    def __init__(self, tool_name: str) -> None:
        """
        Inicializa el error de herramienta inexistente.

        Args:
            tool_name: Nombre de la herramienta solicitada.
        """
        self.tool_name = tool_name

        super().__init__(f"La herramienta '{tool_name}' no está registrada")


class ToolArgumentsError(ToolError):
    """
    Error producido cuando los argumentos de una herramienta no son válidos.

    Se utiliza cuando una herramienta existe, pero los datos recibidos no
    cumplen el esquema, las reglas de negocio o las validaciones requeridas.
    """

    def __init__(
        self,
        tool_name: str,
        details: str,
    ) -> None:
        """
        Inicializa el error de validación de argumentos.

        Args:
            tool_name: Nombre de la herramienta que recibió argumentos inválidos.
            details: Descripción específica del error de validación.
        """
        self.tool_name = tool_name
        self.details = details

        super().__init__(f"Los argumentos de la herramienta '{tool_name}' no son válidos")


class RepositoryError(ApplicationError):
    """
    Error controlado producido al consultar o modificar datos persistentes.
    """


class CustomerConflictError(RepositoryError):
    """
    Indica que no puede registrarse un cliente por un dato único duplicado.
    """

    def __init__(self, field: str) -> None:
        """
        Inicializa el conflicto.

        Args:
            field: Campo duplicado. Debe ser `identification` o `email`.
        """
        self.field = field

        super().__init__(f"Ya existe un cliente con el campo '{field}'")
