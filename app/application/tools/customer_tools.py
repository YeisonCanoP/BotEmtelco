"""
Herramientas para identificar y registrar clientes.

Este módulo contiene las herramientas que el modelo de lenguaje puede invocar
para validar clientes existentes y registrar clientes nuevos durante una
conversación.

Las herramientas funcionan como adaptadores entre el agente conversacional y la
capa de aplicación. No ejecutan consultas SQL directamente ni conocen detalles
de infraestructura. En su lugar, delegan la lógica de clientes a
`CustomerService` y actualizan el estado conversacional mediante
`ConversationContext`.

Responsabilidades principales:

- Buscar clientes por identificación.
- Marcar clientes existentes como verificados dentro de la sesión.
- Iniciar el flujo de registro cuando una identificación no existe.
- Registrar clientes nuevos después de recopilar los datos obligatorios.
- Validar que el registro continúe desde una identificación consultada
  previamente.
- Retornar resultados estructurados para que el agente pueda decidir el
  siguiente paso de la conversación.

"""

from app.application.dtos import (
    CustomerFlowStatus,
    CustomerLookupInputDTO,
    CustomerLookupResultDTO,
    CustomerRegistrationInputDTO,
    CustomerRegistrationResultDTO,
    CustomerResultDTO,
)
from app.application.exceptions import ToolArgumentsError
from app.application.services.conversation_context import ConversationContext
from app.application.services.customer_service import CustomerService
from app.application.tools.base import Tool
from app.domain.entities import Customer


def customer_to_result_dto(
    customer: Customer,
) -> CustomerResultDTO:
    """
    Convierte una entidad de cliente en una salida segura para el agente.

    El DTO resultante contiene únicamente la información mínima necesaria para
    confirmar la identidad del cliente dentro del flujo conversacional.

    No se incluyen teléfono ni correo electrónico porque esos datos no son
    necesarios para continuar la conversación y no deben exponerse si no aportan
    al flujo actual.

    Args:
        customer: Entidad de dominio del cliente encontrado o registrado.

    Returns:
        DTO con la identificación, nombre completo y tipo comercial del cliente.
    """

    return CustomerResultDTO(
        identification=customer.identification,
        full_name=customer.full_name,
        kind=customer.kind,
    )


class FindCustomerTool(
    Tool[
        CustomerLookupInputDTO,
        CustomerLookupResultDTO,
    ]
):
    """
    Herramienta para buscar y validar clientes por identificación.

    Esta herramienta debe usarse cuando el usuario entrega su identificación y
    el agente necesita saber si ya existe como cliente registrado.

    Comportamiento:

    - Si el cliente existe, la conversación queda asociada a ese cliente y su
      estado pasa a verificado.
    - Si el cliente no existe, se inicia el flujo de registro de cliente nuevo.
    - Si inicia el registro, la identificación consultada queda guardada en el
      borrador de registro para evitar registrar otra identificación distinta.
    - Retorna un resultado estructurado indicando si el cliente fue encontrado o
      si requiere registro.

    Esta herramienta es útil antes de ejecutar acciones privadas o sensibles,
    como consultar pedidos, revisar garantías o actualizar información asociada
    al cliente.
    """

    name = "find_customer"

    description = (
        "Busca un cliente por identificación. "
        "Debes usar esta herramienta cuando el usuario entregue su identificación "
        "y sea necesario verificarlo antes de consultar pedidos, garantías u otra "
        "información privada. "
        "Si existe, queda verificado en la sesión. "
        "Si no existe, inicia el flujo de registro. "
        "La identificación debe contener entre 4 y 11 dígitos."
    )

    def __init__(
        self,
        customer_service: CustomerService,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta de búsqueda de clientes.

        Args:
            customer_service: Servicio de aplicación encargado de validar y
                consultar clientes.
            conversation_context: Contexto mutable de la conversación actual.
                Permite actualizar el estado del cliente dentro de la sesión.
        """

        self._customer_service = customer_service
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[CustomerLookupInputDTO]:
        """
        Retorna el modelo de entrada usado por la herramienta.

        El registro de herramientas utiliza este modelo para validar los
        argumentos antes de ejecutar la lógica de búsqueda.

        Returns:
            Clase DTO que define la entrada esperada por `find_customer`.
        """

        return CustomerLookupInputDTO

    async def execute(
        self,
        arguments: CustomerLookupInputDTO,
    ) -> CustomerLookupResultDTO:
        """
        Consulta un cliente por identificación y actualiza la conversación.

        Si el cliente existe, se marca como verificado en el contexto
        conversacional. Si no existe, se inicia el flujo de registro y se guarda
        la identificación consultada como dato pendiente.

        Args:
            arguments: DTO con la identificación validada y normalizada.

        Returns:
            Resultado estructurado de la búsqueda. Indica si el cliente fue
            encontrado o si debe completarse el registro.

        Raises:
            DomainError: Si la identificación no cumple las reglas del dominio.
            RepositoryError: Si ocurre un error al consultar el repositorio.
        """

        customer = await self._customer_service.find_by_identification(arguments.identification)

        if customer is None:
            self._conversation_context.start_registration(arguments.identification)

            return CustomerLookupResultDTO(
                success=True,
                found=False,
                customer=None,
                requires_registration=True,
            )

        self._conversation_context.verify_customer(
            identification=customer.identification,
            full_name=customer.full_name,
        )

        return CustomerLookupResultDTO(
            success=True,
            found=True,
            customer=customer_to_result_dto(customer),
            requires_registration=False,
        )


class RegisterCustomerTool(
    Tool[
        CustomerRegistrationInputDTO,
        CustomerRegistrationResultDTO,
    ]
):
    """
    Herramienta para registrar clientes nuevos.

    Esta herramienta completa el flujo iniciado por `find_customer` cuando una
    identificación no existe en el sistema.

    Reglas del flujo:

    - Primero debe ejecutarse `find_customer`.
    - La conversación debe estar en estado `COLLECTING_REGISTRATION`.
    - La identificación enviada al registro debe coincidir con la identificación
      consultada previamente.
    - El agente debe recopilar identificación, nombre completo, teléfono y
      correo antes de ejecutar esta herramienta.
    - La herramienta no debe completar ni inventar datos faltantes.
    - Si el registro es exitoso, el cliente queda verificado en la sesión.
    - Si hay conflicto por identificación o correo, retorna un resultado
      controlado para que el agente pueda pedir corrección al usuario.

    Esta herramienta no construye respuestas naturales. Solo retorna un DTO con
    el resultado del registro.
    """

    name = "register_customer"

    description = (
        "Registra un cliente nuevo. "
        "Usa esta herramienta solamente después de ejecutar find_customer y "
        "confirmar que la identificación no existe. "
        "Antes de ejecutarla debes recopilar identificación, nombre completo, "
        "teléfono y correo. "
        "No inventes ni completes datos faltantes. "
        "La identificación debe coincidir con la consultada previamente."
    )

    def __init__(
        self,
        customer_service: CustomerService,
        conversation_context: ConversationContext,
    ) -> None:
        """
        Inicializa la herramienta de registro de clientes.

        Args:
            customer_service: Servicio de aplicación encargado de validar,
                normalizar y registrar clientes.
            conversation_context: Contexto mutable de la conversación actual.
                Permite validar el estado del flujo y marcar el cliente como
                verificado después del registro.
        """

        self._customer_service = customer_service
        self._conversation_context = conversation_context

    @property
    def input_model(self) -> type[CustomerRegistrationInputDTO]:
        """
        Retorna el modelo de entrada usado por la herramienta.

        El registro de herramientas utiliza este modelo para validar los datos
        obligatorios del cliente antes de ejecutar el registro.

        Returns:
            Clase DTO que define la entrada esperada por `register_customer`.
        """

        return CustomerRegistrationInputDTO

    async def execute(
        self,
        arguments: CustomerRegistrationInputDTO,
    ) -> CustomerRegistrationResultDTO:
        """
        Registra un cliente nuevo y actualiza la conversación.

        Antes de registrar, valida que la conversación esté en el estado correcto
        y que la identificación enviada coincida con la identificación que fue
        consultada previamente mediante `find_customer`.

        Si el registro se completa correctamente, el cliente queda verificado en
        la sesión. Si ocurre un conflicto controlado, retorna el campo que causó
        el problema.

        Args:
            arguments: DTO con identificación, nombre completo, teléfono y
                correo del cliente.

        Returns:
            Resultado estructurado del registro. Indica si el cliente fue creado
            o si hubo conflicto por identificación o correo.

        Raises:
            ToolArgumentsError: Si se intenta registrar sin ejecutar primero
                `find_customer`, si no hay identificación pendiente o si la
                identificación no coincide con la consultada previamente.
            DomainError: Si algún dato del cliente no cumple las reglas del
                dominio.
            RepositoryError: Si ocurre un fallo inesperado de persistencia.
            RuntimeError: Si el servicio retorna un estado inconsistente sin
                cliente creado ni conflicto identificado.
        """

        conversation = self._conversation_context.conversation

        if conversation.customer_status is not CustomerFlowStatus.COLLECTING_REGISTRATION:
            raise ToolArgumentsError(
                tool_name=self.name,
                details=(
                    "Debes ejecutar find_customer y confirmar que la "
                    "identificación no existe antes de registrar al cliente"
                ),
            )

        expected_identification = conversation.registration_draft.identification

        if expected_identification is None:
            raise ToolArgumentsError(
                tool_name=self.name,
                details=("La conversación no contiene una identificación pendiente de registro"),
            )

        if arguments.identification != expected_identification:
            raise ToolArgumentsError(
                tool_name=self.name,
                details=(
                    "La identificación debe coincidir con la consultada "
                    "previamente mediante find_customer"
                ),
            )

        outcome = await self._customer_service.register(
            identification=arguments.identification,
            full_name=arguments.full_name,
            phone=arguments.phone,
            email=arguments.email,
        )

        if outcome.conflict_field == "identification":
            self._conversation_context.reset_customer()

            return CustomerRegistrationResultDTO(
                success=False,
                created=False,
                customer=None,
                conflict_field="identification",
            )

        if outcome.conflict_field == "email":
            return CustomerRegistrationResultDTO(
                success=False,
                created=False,
                customer=None,
                conflict_field="email",
            )

        if outcome.customer is None:
            raise RuntimeError("El servicio no retornó cliente ni conflicto de registro")

        customer = outcome.customer

        self._conversation_context.verify_customer(
            identification=customer.identification,
            full_name=customer.full_name,
        )

        return CustomerRegistrationResultDTO(
            success=True,
            created=True,
            customer=customer_to_result_dto(customer),
            conflict_field=None,
        )
