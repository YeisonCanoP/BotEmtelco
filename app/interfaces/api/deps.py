"""
Raíz de composición de dependencias de la API.

Este módulo centraliza la creación de dependencias usadas por FastAPI para
procesar las conversaciones del agente.

Su responsabilidad es construir y conectar las piezas concretas de la
aplicación sin mezclar esa lógica dentro de endpoints, servicios o herramientas.

Desde este archivo se ensamblan:

- Repositorios de infraestructura.
- Servicios de aplicación.
- Contexto mutable de conversación.
- Registro de herramientas disponibles para el agente.
- Proveedor LLM.
- Almacenamiento de sesiones.
- Servicio principal del agente conversacional.

"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports.llm_provider import LLMProvider
from app.application.ports.repositories import (
    CatalogRepository,
    CustomerRepository,
)
from app.application.ports.session_store import SessionStore
from app.application.services.agent_service import AgentService
from app.application.services.conversation_context import (
    ConversationContext,
)
from app.application.services.customer_service import CustomerService
from app.application.tools import (
    CompareProductsTool,
    FindCustomerTool,
    RegisterCustomerTool,
    SearchCatalogTool,
    ToolRegistry,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.config import get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.repositories.sql_catalog import (
    SqlCatalogRepository,
)
from app.infrastructure.repositories.sql_customers import (
    SqlCustomerRepository,
)
from app.infrastructure.session.redis_session_store import (
    RedisSessionStore,
)

DbSession = Annotated[
    Session,
    Depends(get_db),
]


def get_catalog_repository(
    db: DbSession,
) -> CatalogRepository:
    """
    Construye el repositorio de catálogo para la petición actual.

    El repositorio concreto usa SQLAlchemy para consultar productos almacenados
    en PostgreSQL, pero se expone mediante el puerto `CatalogRepository` para
    mantener desacoplada la capa de aplicación.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación concreta del repositorio de catálogo.
    """

    return SqlCatalogRepository(db)


CatalogDependency = Annotated[
    CatalogRepository,
    Depends(get_catalog_repository),
]


def get_customer_repository(
    db: DbSession,
) -> CustomerRepository:
    """
    Construye el repositorio de clientes para la petición actual.

    El repositorio concreto consulta y registra clientes usando PostgreSQL, pero
    se entrega como `CustomerRepository` para que los servicios de aplicación no
    dependan de SQLAlchemy.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación concreta del repositorio de clientes.
    """

    return SqlCustomerRepository(db)


CustomerRepositoryDependency = Annotated[
    CustomerRepository,
    Depends(get_customer_repository),
]


def get_customer_service(
    repository: CustomerRepositoryDependency,
) -> CustomerService:
    """
    Construye el servicio de clientes para la petición actual.

    Este servicio coordina los casos de uso de consulta y registro de clientes.
    Recibe un repositorio mediante el puerto `CustomerRepository`.

    Args:
        repository: Repositorio usado para consultar y registrar clientes.

    Returns:
        Servicio de aplicación para operaciones de clientes.
    """

    return CustomerService(repository)


CustomerServiceDependency = Annotated[
    CustomerService,
    Depends(get_customer_service),
]


def get_conversation_context() -> ConversationContext:
    """
    Crea el contexto mutable de conversación para la petición actual.

    Este contexto permite que `AgentService` y las herramientas trabajen sobre
    el mismo objeto `ConversationDTO` durante el procesamiento de un mensaje.

    No debe usar `lru_cache`, porque contiene estado mutable asociado a una
    petición específica. Si fuera global, una conversación podría contaminar el
    estado de otra sesión.

    FastAPI reutiliza la misma instancia dentro de una misma petición cuando la
    dependencia se solicita varias veces, por ejemplo en `ToolRegistry` y
    `AgentService`.

    Returns:
        Contexto conversacional vacío, listo para enlazarse a una conversación.
    """

    return ConversationContext()


ConversationContextDependency = Annotated[
    ConversationContext,
    Depends(get_conversation_context),
]


def get_tool_registry(
    catalog_repository: CatalogDependency,
    customer_service: CustomerServiceDependency,
    conversation_context: ConversationContextDependency,
) -> ToolRegistry:
    """
    Construye el registro de herramientas disponibles para la petición actual.

    Las herramientas se crean por petición porque algunas dependen del contexto
    mutable de conversación. Esto permite que herramientas de clientes actualicen
    el estado estructurado de la sesión, por ejemplo cliente verificado,
    borrador de registro o acción pendiente.

    Herramientas registradas:

    - `SearchCatalogTool`: busca productos en el catálogo.
    - `CompareProductsTool`: compara productos por SKU.
    - `FindCustomerTool`: valida si una identificación pertenece a un cliente.
    - `RegisterCustomerTool`: registra clientes nuevos después de validar el
      flujo correspondiente.

    Args:
        catalog_repository: Repositorio usado por herramientas de catálogo.
        customer_service: Servicio usado por herramientas de clientes.
        conversation_context: Contexto compartido entre herramientas y agente.

    Returns:
        Registro de herramientas disponible para el proveedor LLM.
    """

    return ToolRegistry(
        tools=[
            SearchCatalogTool(catalog_repository),
            CompareProductsTool(catalog_repository),
            FindCustomerTool(
                customer_service=customer_service,
                conversation_context=conversation_context,
            ),
            RegisterCustomerTool(
                customer_service=customer_service,
                conversation_context=conversation_context,
            ),
        ]
    )


ToolRegistryDependency = Annotated[
    ToolRegistry,
    Depends(get_tool_registry),
]


@lru_cache
def get_session_store() -> SessionStore:
    """
    Construye el almacenamiento Redis de conversaciones.

    Esta dependencia puede almacenarse en caché porque la instancia no contiene
    el estado de una conversación concreta. Solo conserva configuración y acceso
    al cliente Redis.

    El estado real de cada sesión se almacena en Redis usando el identificador
    de conversación como parte de la clave.

    Returns:
        Implementación Redis del puerto `SessionStore`.
    """

    settings = get_settings()

    return RedisSessionStore(
        client=get_redis_client(),
        ttl_seconds=settings.redis_session_ttl_seconds,
        key_prefix=settings.redis_session_prefix,
    )


SessionStoreDependency = Annotated[
    SessionStore,
    Depends(get_session_store),
]


@lru_cache
def get_llm_provider() -> LLMProvider:
    """
    Construye el proveedor LLM reutilizable.

    Esta dependencia puede mantenerse en caché porque el proveedor no almacena
    estado conversacional mutable. Su responsabilidad es comunicarse con el
    modelo de lenguaje configurado para el agente.

    Returns:
        Implementación concreta del puerto `LLMProvider`.
    """

    return OpenAIProvider()


LLMProviderDependency = Annotated[
    LLMProvider,
    Depends(get_llm_provider),
]


def get_agent_service(
    llm_provider: LLMProviderDependency,
    session_store: SessionStoreDependency,
    tool_registry: ToolRegistryDependency,
    conversation_context: ConversationContextDependency,
) -> AgentService:
    """
    Construye el servicio principal del agente para la petición actual.

    El servicio recibe todas las piezas necesarias para procesar un mensaje:

    - Proveedor LLM.
    - Almacenamiento de sesiones.
    - Registro de herramientas.
    - Contexto conversacional compartido.
    - Límite de rondas de herramientas.

    El mismo `ConversationContext` inyectado aquí también se entrega a las
    herramientas mediante `ToolRegistry`, permitiendo que todos trabajen sobre
    la misma conversación durante la petición.

    Args:
        llm_provider: Proveedor usado para generar respuestas del agente.
        session_store: Almacenamiento usado para recuperar y guardar sesiones.
        tool_registry: Registro de herramientas disponibles para el agente.
        conversation_context: Contexto mutable compartido con las herramientas.

    Returns:
        Servicio principal del agente conversacional.
    """

    settings = get_settings()

    return AgentService(
        llm_provider=llm_provider,
        session_store=session_store,
        tool_registry=tool_registry,
        conversation_context=conversation_context,
        max_tool_rounds=settings.agent_max_tool_rounds,
    )


AgentDependency = Annotated[
    AgentService,
    Depends(get_agent_service),
]
