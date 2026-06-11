"""
DTOs utilizados por el flujo conversacional del agente.

Este módulo define los modelos de transferencia de datos relacionados con
mensajes, sesiones conversacionales, identificación de clientes, registro de
clientes nuevos y solicitudes/respuestas del servicio principal del agente.

Los DTOs permiten normalizar la comunicación entre la capa de entrada
por ejemplo, endpoints HTTP, la capa de aplicación y los casos de uso del
agente, evitando exponer directamente modelos internos o entidades de dominio.

También conservan información relevante de la sesión para que el agente pueda
continuar flujos interrumpidos, como consultar pedidos, actualizar direcciones
o registrar solicitudes de garantía después de validar o registrar al cliente.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MessageRole(StrEnum):
    """
    Roles permitidos para los mensajes dentro de una conversación.

    El rol indica quién produjo cada mensaje dentro del historial
    conversacional. Esta información es necesaria para reconstruir el contexto
    enviado al modelo de lenguaje y diferenciar los mensajes del usuario de las
    respuestas generadas por el asistente.

    Attributes:
        USER: Mensaje enviado por el usuario final.
        ASSISTANT: Mensaje generado por el agente o asistente.
    """

    USER = "user"
    ASSISTANT = "assistant"


class CustomerFlowStatus(StrEnum):
    """
    Estado de identificación del cliente dentro de la conversación.

    Este estado permite saber si el agente ya puede ejecutar operaciones
    sensibles asociadas al cliente, como consultar pedidos, actualizar datos de
    entrega o crear solicitudes de garantía.

    Attributes:
        UNIDENTIFIED: El cliente aún no ha sido identificado ni validado.
        COLLECTING_REGISTRATION: El agente está recopilando datos para registrar
            un cliente nuevo.
        VERIFIED: El cliente ya fue identificado o registrado correctamente.
    """

    UNIDENTIFIED = "UNIDENTIFIED"
    COLLECTING_REGISTRATION = "COLLECTING_REGISTRATION"
    VERIFIED = "VERIFIED"


class PendingAction(StrEnum):
    """
    Operación pendiente dentro del flujo conversacional.

    Se utiliza cuando el usuario solicita una acción que requiere validar o
    registrar al cliente antes de ejecutarse. Una vez el cliente queda
    verificado, el agente puede retomar la operación original usando este valor.

    Attributes:
        LIST_ORDERS: Consultar los pedidos asociados al cliente.
        GET_ORDER_STATUS: Consultar el estado de un pedido específico.
        UPDATE_ORDER_ADDRESS: Actualizar la dirección de entrega de un pedido.
        CHECK_WARRANTY: Consultar la cobertura o estado de garantía.
        CREATE_WARRANTY_CLAIM: Registrar una solicitud de garantía.
    """

    LIST_ORDERS = "LIST_ORDERS"
    GET_ORDER_STATUS = "GET_ORDER_STATUS"
    UPDATE_ORDER_ADDRESS = "UPDATE_ORDER_ADDRESS"
    CHECK_WARRANTY = "CHECK_WARRANTY"
    CREATE_WARRANTY_CLAIM = "CREATE_WARRANTY_CLAIM"


class ChatMessageDTO(BaseModel):
    """
    Representa un mensaje individual dentro de una conversación.

    Cada mensaje contiene el rol del emisor y el contenido textual asociado.
    Este DTO se utiliza para almacenar, transportar y reconstruir el historial
    conversacional de una sesión.

    Attributes:
        role: Rol del autor del mensaje. Puede ser `user` o `assistant`.
        content: Contenido textual del mensaje. Debe tener al menos un carácter
            y no superar los 20.000 caracteres.
    """

    role: MessageRole
    content: str = Field(
        min_length=1,
        max_length=20_000,
    )


class CustomerRegistrationDraftDTO(BaseModel):
    """
    Datos parciales recopilados durante el registro de un cliente nuevo.

    Todos los campos son opcionales porque el usuario puede entregar la
    información en mensajes separados. El agente debe conservar estos datos
    mientras completa el flujo de registro.

    Attributes:
        identification: Identificación del cliente. Debe tener entre 4 y 11
            dígitos numéricos.
        full_name: Nombre completo del cliente. Debe tener entre 1 y 100
            caracteres y contener únicamente letras, espacios, tildes y ñ.
        phone: Número telefónico del cliente. Debe tener exactamente 10 dígitos
            e iniciar por 3 o 6.
        email: Correo electrónico del cliente. Debe tener formato básico de
            email válido.
    """

    identification: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4,11}$",
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$",
    )
    phone: str | None = Field(
        default=None,
        pattern=r"^[36][0-9]{9}$",
    )
    email: str | None = Field(
        default=None,
        min_length=3,
        max_length=150,
        pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
    )

    def missing_fields(self) -> list[str]:
        """
        Retorna los campos requeridos que aún no han sido recopilados.

        Este métod permite que el agente determine qué dato debe solicitar a
        continuación durante el flujo de registro de cliente nuevo.

        Returns:
            Lista con los nombres técnicos de los campos faltantes.
        """

        missing: list[str] = []

        if self.identification is None:
            missing.append("identification")

        if self.full_name is None:
            missing.append("full_name")

        if self.phone is None:
            missing.append("phone")

        if self.email is None:
            missing.append("email")

        return missing

    @property
    def is_complete(self) -> bool:
        """
        Indica si el borrador de registro ya tiene todos los datos requeridos.

        Returns:
            `True` si no falta ningún campo obligatorio. De lo contrario,
            retorna `False`.
        """

        return not self.missing_fields()


class ConversationDTO(BaseModel):
    """
    Representa el estado completo y persistente de una conversación.

    Este DTO agrupa el identificador único de la sesión, el historial visible de
    mensajes, el estado de identificación del cliente, los datos parciales de
    registro y la operación pendiente que debe retomarse después de validar al
    cliente.

    Sirve para conservar el contexto conversacional a lo largo de la sesión y
    evitar que el agente pierda información relevante entre mensajes.

    Attributes:
        session_id: Identificador único de la sesión conversacional.
        messages: Lista ordenada de mensajes asociados a la conversación.
        customer_status: Estado actual del cliente dentro del flujo.
        verified_customer_id: Identificación del cliente ya validado.
        verified_customer_name: Nombre del cliente ya validado.
        registration_draft: Datos parciales recopilados para registrar un
            cliente nuevo.
        pending_action: Acción que debe retomarse después de identificar o
            registrar al cliente.
        pending_reference: Referencia asociada a la acción pendiente, como un
            número de pedido, producto, ticket o garantía.
    """

    session_id: UUID

    messages: list[ChatMessageDTO] = Field(
        default_factory=list,
    )

    customer_status: CustomerFlowStatus = CustomerFlowStatus.UNIDENTIFIED

    verified_customer_id: str | None = Field(
        default=None,
        pattern=r"^[0-9]{4,11}$",
    )

    verified_customer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    registration_draft: CustomerRegistrationDraftDTO = Field(
        default_factory=CustomerRegistrationDraftDTO,
    )

    pending_action: PendingAction | None = None

    pending_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )


class AgentRequestDTO(BaseModel):
    """
    Representa la entrada del caso de uso principal del agente.

    Este DTO se usa cuando el usuario envía un nuevo mensaje al agente. Incluye
    la sesión a la que pertenece el mensaje y el texto que debe procesarse.

    Attributes:
        session_id: Identificador de la sesión asociada al mensaje del usuario.
        message: Mensaje enviado por el usuario. Debe tener al menos un carácter
            y no superar los 4.000 caracteres.
    """

    session_id: UUID
    message: str = Field(
        min_length=1,
        max_length=4_000,
    )


class AgentResponseDTO(BaseModel):
    """
    Representa la respuesta final generada por el agente.

    Este DTO se retorna después de procesar el mensaje del usuario, ejecutar la
    lógica conversacional y, si aplica, invocar herramientas externas como
    catálogo, pedidos o garantías.

    Attributes:
        session_id: Identificador de la sesión asociada a la respuesta.
        reply: Texto final que será entregado al usuario.
    """

    session_id: UUID
    reply: str = Field(min_length=1)
