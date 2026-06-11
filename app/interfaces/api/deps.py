"""
Raíz de composición de dependencias de la API.

Este módulo centraliza la creación de dependencias usadas por FastAPI para
procesar las conversaciones del agente.

Su responsabilidad es construir, conectar y exponer las implementaciones
concretas que necesita la aplicación, sin mezclar esta lógica dentro de
endpoints, servicios, herramientas o casos de uso.

Desde este archivo se ensamblan:

    - Repositorios de infraestructura.
    - Servicios de aplicación.
    - Contexto mutable de conversación.
    - Registro de herramientas disponibles para el agente.
    - Proveedor LLM.
    - Proveedor de embeddings.
    - Almacenamiento vectorial.
    - Servicio de recuperación semántica.
    - Almacenamiento de sesiones.
    - Servicio principal del agente conversacional.

"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.application.ports.embedding_provider import EmbeddingProvider
from app.application.ports.llm_provider import LLMProvider
from app.application.ports.repositories import (
    CatalogRepository,
    CustomerRepository,
    HumanHandoffRepository,
    OrderRepository,
    WarrantyRepository,
)
from app.application.ports.session_store import SessionStore
from app.application.ports.vector_store import VectorStore
from app.application.services.agent_service import AgentService
from app.application.services.conversation_context import (
    ConversationContext,
)
from app.application.services.customer_service import CustomerService
from app.application.services.retrieval_service import RetrievalService
from app.application.tools import (
    CheckWarrantyTool,
    CompareProductsTool,
    EscalateWarrantyClaimTool,
    FindCustomerTool,
    GetCustomerOrderTool,
    ListCustomerOrdersTool,
    RegisterCustomerTool,
    RegisterWarrantyClaimTool,
    RequestHumanSupportTool,
    SearchCatalogTool,
    SearchKnowledgeBaseTool,
    ToolRegistry,
    UpdateOrderAddressTool,
)
from app.infrastructure.cache.redis_client import get_redis_client
from app.infrastructure.config import get_settings
from app.infrastructure.db.session import get_db
from app.infrastructure.llm.openai_embedding_provider import (
    OpenAIEmbeddingProvider,
)
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.repositories.sql_catalog import (
    SqlCatalogRepository,
)
from app.infrastructure.repositories.sql_customers import (
    SqlCustomerRepository,
)
from app.infrastructure.repositories.sql_handoffs import (
    SqlHumanHandoffRepository,
)
from app.infrastructure.repositories.sql_orders import SqlOrderRepository
from app.infrastructure.repositories.sql_warranties import (
    SqlWarrantyRepository,
)
from app.infrastructure.session.redis_session_store import (
    RedisSessionStore,
)
from app.infrastructure.vectorstore.pgvector_store import PgVectorStore

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
    dependan directamente de SQLAlchemy.

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


def get_order_repository(
    db: DbSession,
) -> OrderRepository:
    """
    Construye el repositorio de pedidos para la petición actual.

    El repositorio concreto permite listar pedidos, consultar pedidos por
    cliente y actualizar direcciones de entrega usando PostgreSQL.

    Todas las operaciones quedan asociadas a la misma sesión SQLAlchemy de la
    petición actual.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación concreta del repositorio de pedidos.
    """

    return SqlOrderRepository(db)


OrderRepositoryDependency = Annotated[
    OrderRepository,
    Depends(get_order_repository),
]


def get_warranty_repository(
    db: DbSession,
) -> WarrantyRepository:
    """
    Construye el repositorio de garantías para la petición actual.

    El repositorio consulta garantías, registra reclamos técnicos y escala
    tickets mediante PostgreSQL.

    Todas las operaciones sensibles validan que el pedido, la garantía o el
    ticket pertenezcan al cliente verificado en la conversación.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación PostgreSQL del repositorio de garantías.
    """

    return SqlWarrantyRepository(db)


WarrantyRepositoryDependency = Annotated[
    WarrantyRepository,
    Depends(get_warranty_repository),
]


def get_human_handoff_repository(
    db: DbSession,
) -> HumanHandoffRepository:
    """
    Construye el repositorio de solicitudes generales de atención humana.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación PostgreSQL del repositorio de escalamiento general.
    """

    return SqlHumanHandoffRepository(db)


HumanHandoffRepositoryDependency = Annotated[
    HumanHandoffRepository,
    Depends(get_human_handoff_repository),
]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """
    Construye el proveedor reutilizable de embeddings.

    Esta dependencia se mantiene en caché porque el proveedor no contiene estado
    conversacional mutable. Solo encapsula configuración y acceso al proveedor
    externo de embeddings.

    Returns:
        Implementación OpenAI del puerto `EmbeddingProvider`.
    """

    return OpenAIEmbeddingProvider()


EmbeddingProviderDependency = Annotated[
    EmbeddingProvider,
    Depends(get_embedding_provider),
]


def get_vector_store(
    db: DbSession,
) -> VectorStore:
    """
    Construye el almacenamiento vectorial para la petición actual.

    La instancia usa la misma sesión SQLAlchemy de la petición. Esto permite que
    las operaciones sobre `kb_chunks` participen en el mismo ciclo de vida de
    base de datos que el resto de adaptadores de infraestructura.

    Args:
        db: Sesión SQLAlchemy activa de la petición.

    Returns:
        Implementación pgvector del puerto `VectorStore`.
    """

    return PgVectorStore(db=db)


VectorStoreDependency = Annotated[
    VectorStore,
    Depends(get_vector_store),
]


def get_retrieval_service(
    embedding_provider: EmbeddingProviderDependency,
    vector_store: VectorStoreDependency,
) -> RetrievalService:
    """
    Construye el servicio de recuperación semántica.

    Este servicio coordina la generación de embeddings y la búsqueda vectorial
    sobre la base de conocimiento.

    Args:
        embedding_provider: Proveedor usado para convertir consultas en
            embeddings.
        vector_store: Almacenamiento vectorial usado para buscar fragmentos
            similares.

    Returns:
        Servicio de recuperación semántica configurado con umbral mínimo de
        similitud.
    """

    return RetrievalService(
        embeddings=embedding_provider,
        vector_store=vector_store,
        score_threshold=0.7,
    )


RetrievalServiceDependency = Annotated[
    RetrievalService,
    Depends(get_retrieval_service),
]


def get_customer_service(
    repository: CustomerRepositoryDependency,
) -> CustomerService:
    """
    Construye el servicio de clientes para la petición actual.

    Este servicio coordina los casos de uso relacionados con identificación,
    validación y registro de clientes.

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
    order_repository: OrderRepositoryDependency,
    warranty_repository: WarrantyRepositoryDependency,
    human_handoff_repository: HumanHandoffRepositoryDependency,
    retrieval_service: RetrievalServiceDependency,
    conversation_context: ConversationContextDependency,
) -> ToolRegistry:
    """
    Construye el registro de herramientas disponibles para la petición actual.

    Las herramientas se crean por petición porque algunas dependen del contexto
    mutable de conversación. Esto permite que herramientas de clientes, pedidos,
    garantías y escalamiento actualicen el estado estructurado de la sesión.

    Herramientas registradas:
        - `SearchCatalogTool`: busca productos en el catálogo.
        - `CompareProductsTool`: compara productos por SKU.
        - `FindCustomerTool`: valida si una identificación pertenece a un
          cliente.
        - `RegisterCustomerTool`: registra clientes nuevos.
        - `ListCustomerOrdersTool`: lista pedidos del cliente verificado.
        - `GetCustomerOrderTool`: consulta un pedido del cliente verificado.
        - `UpdateOrderAddressTool`: actualiza la dirección de entrega de un
          pedido.
        - `CheckWarrantyTool`: valida cobertura de garantía.
        - `RegisterWarrantyClaimTool`: registra un reclamo y genera su ticket.
        - `EscalateWarrantyClaimTool`: escala un ticket a atención humana.
        - `RequestHumanSupportTool`: transfiere una conversación general a un
          asesor humano.
        - `SearchKnowledgeBaseTool`: consulta políticas, procedimientos y
          preguntas frecuentes mediante búsqueda semántica.

    Args:
        catalog_repository: Repositorio usado por herramientas de catálogo.
        customer_service: Servicio usado por herramientas de clientes.
        order_repository: Repositorio usado por herramientas de pedidos.
        warranty_repository: Repositorio usado por herramientas de garantías.
        human_handoff_repository: Repositorio usado para escalamiento general.
        retrieval_service: Servicio usado por la herramienta de búsqueda en base
            de conocimiento.
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
            ListCustomerOrdersTool(
                repository=order_repository,
                conversation_context=conversation_context,
            ),
            GetCustomerOrderTool(
                repository=order_repository,
                conversation_context=conversation_context,
            ),
            UpdateOrderAddressTool(
                repository=order_repository,
                conversation_context=conversation_context,
            ),
            CheckWarrantyTool(
                repository=warranty_repository,
                conversation_context=conversation_context,
            ),
            RegisterWarrantyClaimTool(
                repository=warranty_repository,
                conversation_context=conversation_context,
            ),
            EscalateWarrantyClaimTool(
                repository=warranty_repository,
                conversation_context=conversation_context,
            ),
            RequestHumanSupportTool(
                repository=human_handoff_repository,
                conversation_context=conversation_context,
            ),
            SearchKnowledgeBaseTool(
                retrieval_service=retrieval_service,
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
