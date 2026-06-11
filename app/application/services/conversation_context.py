"""
Contexto mutable de la conversación actual.

Este módulo define una capa auxiliar para compartir el estado conversacional
entre el servicio principal del agente y las herramientas ejecutadas durante
una misma petición.

La conversación se recupera desde el almacenamiento de sesión, por ejemplo
Redis, al inicio del flujo. Luego se enlaza a `ConversationContext` para que
las herramientas puedan consultar y modificar información relevante como:

- Cliente validado en la sesión.
- Datos parciales de registro de un cliente nuevo.
- Operación pendiente por retomar.
- Referencias asociadas a pedidos, productos o garantías.

Al finalizar el procesamiento del mensaje, el servicio principal debe persistir
nuevamente la conversación actualizada.
"""

from app.application.dtos.chat import (
    ConversationDTO,
    CustomerFlowStatus,
    CustomerRegistrationDraftDTO,
    PendingAction,
)


class ConversationContext:
    """
    Administra el estado conversacional activo durante una petición.

    Esta clase no crea ni persiste conversaciones por sí misma. Su
    responsabilidad es mantener una referencia en memoria al `ConversationDTO`
    cargado previamente por el servicio de aplicación.

    El objetivo es evitar pasar manualmente la conversación a cada herramienta.
    En su lugar, las herramientas reciben este contexto y modifican el mismo
    objeto compartido.

    Attributes:
        _conversation: Conversación actualmente enlazada al contexto. Permanece
            en `None` hasta que el servicio invoque `bind`.
    """

    def __init__(self) -> None:
        """
        Inicializa el contexto sin una conversación asociada.

        La conversación debe enlazarse explícitamente mediante `bind` antes de
        usar cualquier propiedad o métod que dependa del estado de sesión.
        """

        self._conversation: ConversationDTO | None = None

    def bind(self, conversation: ConversationDTO) -> None:
        """
        Asocia una conversación al contexto actual.

        Normalmente este métodse invoca al inicio de una petición, después de
        recuperar la conversación desde Redis o después de crear una nueva
        sesión.

        Args:
            conversation: Conversación que será compartida entre el agente y
                sus herramientas durante el procesamiento del mensaje.
        """

        self._conversation = conversation

    @property
    def conversation(self) -> ConversationDTO:
        """
        Retorna la conversación actualmente asociada al contexto.

        Returns:
            Conversación activa de la sesión.

        Raises:
            RuntimeError: Si el contexto se usa antes de enlazar una
                conversación mediante `bind`.
        """

        if self._conversation is None:
            raise RuntimeError("ConversationContext no está asociado a una conversación")

        return self._conversation

    @property
    def is_customer_verified(self) -> bool:
        """
        Indica si la sesión tiene un cliente validado.

        Un cliente se considera validado cuando el estado del flujo es
        `VERIFIED` y existe una identificación asociada a la conversación.

        Returns:
            `True` si el cliente ya fue identificado o registrado
            correctamente. De lo contrario, retorna `False`.
        """

        return (
            self.conversation.customer_status is CustomerFlowStatus.VERIFIED
            and self.conversation.verified_customer_id is not None
        )

    @property
    def verified_customer_id(self) -> str | None:
        """
        Retorna la identificación del cliente validado.

        Esta propiedad permite que herramientas de pedidos, garantías o soporte
        consulten el cliente actual sin acceder directamente a todos los campos
        de la conversación.

        Returns:
            Identificación del cliente validado, o `None` si la sesión todavía
            no tiene cliente asociado.
        """

        return self.conversation.verified_customer_id

    def start_registration(self, identification: str) -> None:
        """
        Inicia el flujo de registro para un cliente nuevo.

        Este métod se usa cuando el agente identifica que la persona no existe
        previamente en el sistema y debe recopilar sus datos obligatorios.

        Al iniciar el registro se limpia cualquier cliente verificado anterior y
        se crea un borrador con la identificación ya capturada.

        Args:
            identification: Número de identificación entregado por el usuario.
                Debe cumplir la validación definida en `ConversationDTO`.
        """

        conversation = self.conversation

        conversation.customer_status = CustomerFlowStatus.COLLECTING_REGISTRATION
        conversation.verified_customer_id = None
        conversation.verified_customer_name = None
        conversation.registration_draft = CustomerRegistrationDraftDTO(
            identification=identification,
        )

    def verify_customer(
        self,
        identification: str,
        full_name: str,
    ) -> None:
        """
        Marca al cliente de la sesión como verificado.

        Aplica tanto para clientes frecuentes encontrados en el sistema como
        para clientes nuevos registrados exitosamente durante la conversación.

        Después de verificar al cliente, el borrador de registro se reinicia
        porque ya no quedan datos pendientes por recolectar.

        Args:
            identification: Identificación validada del cliente.
            full_name: Nombre completo asociado al cliente validado.
        """

        conversation = self.conversation

        conversation.customer_status = CustomerFlowStatus.VERIFIED
        conversation.verified_customer_id = identification
        conversation.verified_customer_name = full_name
        conversation.registration_draft = CustomerRegistrationDraftDTO()

    def reset_customer(self) -> None:
        """
        Elimina la identidad del cliente asociada a la sesión.

        Este métod devuelve la conversación al estado inicial de identificación.
        Puede usarse cuando el usuario desea cambiar de cliente, cerrar el flujo
        actual o corregir una identificación entregada previamente.

        También limpia el borrador de registro para evitar mezclar datos de
        clientes distintos.
        """

        conversation = self.conversation

        conversation.customer_status = CustomerFlowStatus.UNIDENTIFIED
        conversation.verified_customer_id = None
        conversation.verified_customer_name = None
        conversation.registration_draft = CustomerRegistrationDraftDTO()

    def set_pending_action(
        self,
        action: PendingAction,
        reference: str | None = None,
    ) -> None:
        """
        Guarda una operación pendiente por retomar.

        Se utiliza cuando el usuario solicita una acción que no puede resolverse
        inmediatamente porque falta identificar al cliente, completar el
        registro o pedir información adicional.

        Ejemplos de acciones pendientes:

        - Consultar el estado de un pedido.
        - Actualizar la dirección de entrega.
        - Validar o registrar una garantía.
        - Consultar, comparar o recomendar productos si falta algún dato clave.

        Args:
            action: Operación que el agente debe continuar más adelante.
            reference: Dato asociado a la operación pendiente, como número de
                pedido, nombre del producto, identificador de garantía o una
                descripción breve de la necesidad del cliente.
        """

        conversation = self.conversation

        conversation.pending_action = action
        conversation.pending_reference = reference

    def clear_pending_action(self) -> None:
        """
        Limpia la operación pendiente de la conversación.

        Debe invocarse cuando la acción guardada ya fue ejecutada, cancelada o
        dejó de ser necesaria. Esto evita que el agente repita operaciones
        antiguas en mensajes posteriores.
        """

        conversation = self.conversation

        conversation.pending_action = None
        conversation.pending_reference = None
