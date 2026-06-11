# Agente IA para atención de una tienda retail

Aplicación conversacional para una tienda de productos electrónicos. El agente atiende consultas
de catálogo, compara productos, valida clientes, consulta pedidos, gestiona garantías y puede
transferir una conversación a atención humana.

El proyecto usa FastAPI como API, Streamlit como interfaz web, PostgreSQL para la información
transaccional, pgvector para búsqueda semántica, Redis para conservar las sesiones y OpenAI para
la generación de respuestas y embeddings.

## Funcionalidades

- Búsqueda de productos por categoría, uso, presupuesto y especificaciones.
- Comparación de productos por SKU.
- Validación y registro de clientes.
- Consulta del historial y estado de pedidos.
- Actualización de direcciones para pedidos en estado `CONFIRMED` o `PREPARING`.
- Consulta de cobertura de garantías.
- Creación de reclamos de garantía y generación de tickets.
- Escalamiento de tickets a atención humana.
- Solicitud general de un asesor, incluso si el cliente no se ha identificado.
- Consulta de políticas, preguntas frecuentes y guías mediante RAG con pgvector.
- Memoria conversacional en Redis con tiempo de expiración configurable.
- Interfaz de chat en Streamlit.

## Tecnologías principales

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| API | FastAPI |
| Servidor ASGI | Uvicorn |
| Interfaz web | Streamlit |
| Base de datos | PostgreSQL 16 |
| Búsqueda vectorial | pgvector |
| ORM | SQLAlchemy 2 |
| Sesiones | Redis 7 |
| Modelos y validación | Pydantic 2 |
| Proveedor de IA | OpenAI Responses API |
| Gestión de dependencias | uv |
| Pruebas y calidad | pytest, Ruff y Pyrefly |
| Contenedores | Docker Compose |

## Arquitectura

El código sigue una separación por capas. El dominio no depende de FastAPI, SQLAlchemy, Redis ni
OpenAI; las integraciones concretas se conectan mediante puertos definidos por la aplicación.

```mermaid
flowchart LR
    User[Usuario] --> UI[Streamlit]
    UI --> API[FastAPI]
    API --> Agent[AgentService]
    Agent --> LLM[OpenAI Responses API]
    Agent --> Tools[ToolRegistry]
    Agent --> Sessions[(Redis)]
    Tools --> Repositories[Repositorios SQL]
    Repositories --> DB[(PostgreSQL)]
    Tools --> Retrieval[RetrievalService]
    Retrieval --> Embeddings[OpenAI Embeddings]
    Retrieval --> VectorStore[(pgvector)]
```

Responsabilidad de cada capa:

- `app/domain`: entidades, objetos de valor y reglas independientes de infraestructura.
- `app/application`: DTO, servicios, puertos, herramientas y prompt del agente.
- `app/infrastructure`: configuración, PostgreSQL, Redis, OpenAI, repositorios y pgvector.
- `app/interfaces`: rutas HTTP, esquemas de entrada/salida, dependencias y middleware.
- `frontend`: cliente Streamlit que consume la API.

El ensamblado de dependencias está centralizado en `app/interfaces/api/deps.py`. Allí se registran
las herramientas que el modelo puede ejecutar y se conectan con sus repositorios o servicios.

## Estructura del repositorio

```text
.
├── app/
│   ├── application/          # Casos de uso, DTO, herramientas, puertos y prompt
│   ├── domain/               # Entidades y objetos de valor
│   ├── infrastructure/       # PostgreSQL, Redis, OpenAI, pgvector y configuración
│   ├── interfaces/api/       # Endpoints, esquemas y dependencias de FastAPI
│   ├── scripts/              # Carga de embeddings y utilidades
│   └── main.py               # Creación de la aplicación FastAPI
├── database/init.sql         # Esquema, restricciones y datos iniciales
├── frontend/streamlit_app.py # Interfaz de chat
├── knowledge/                # Documentos de referencia de la base de conocimiento
├── modelado_datos/           # Diagrama entidad-relación en Mermaid
├── tests/                    # Pruebas automatizadas
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Requisitos

Para ejecutar todo con Docker:

- Docker Engine.
- Docker Compose v2.
- Una API key de OpenAI con acceso al modelo conversacional y al modelo de embeddings.

Para desarrollo local:

- Python 3.12.
- [uv](https://docs.astral.sh/uv/).
- PostgreSQL con la extensión pgvector y Redis. La forma más sencilla es iniciar solo esos dos
  servicios con Docker Compose.

## Variables de entorno

Crea el archivo local a partir de la plantilla:

```bash
cp .env.example .env
```

Después configura como mínimo:

```dotenv
OPENAI_API_KEY=tu_api_key
```

No subas `.env` al repositorio. La plantilla `.env.example` contiene valores de desarrollo y no
debe incluir credenciales reales.

### Aplicación y conexiones

| Variable | Valor de ejemplo | Uso |
|---|---|---|
| `APP_ENV` | `development` | Nombre del entorno de ejecución. |
| `API_BASE_URL` | `http://localhost:8000` | URL que usa el frontend cuando se ejecuta localmente. |
| `DATABASE_URL` | `postgresql+psycopg://postgres:postgres@localhost:5433/retail_ai` | Conexión SQLAlchemy a PostgreSQL. |
| `REDIS_URL` | `redis://localhost:6379/0` | Conexión al almacenamiento de sesiones. |
| `REDIS_SESSION_TTL_SECONDS` | `86400` | Duración de una sesión en segundos. |
| `REDIS_SESSION_PREFIX` | `retail-ai:session` | Prefijo de las claves guardadas en Redis. |

### OpenAI y agente

| Variable | Valor de ejemplo | Uso |
|---|---|---|
| `OPENAI_API_KEY` | sin valor | Credencial requerida para chat y embeddings. |
| `OPENAI_MODEL` | `gpt-5-mini` | Modelo usado por el agente. |
| `OPENAI_REASONING_EFFORT` | `medium` | Esfuerzo de razonamiento: `minimal`, `low`, `medium` o `high`. |
| `OPENAI_VERBOSITY` | `low` | Nivel de detalle: `low`, `medium` o `high`. |
| `OPENAI_MAX_OUTPUT_TOKENS` | `5000` | Límite de tokens de salida por respuesta. |
| `OPENAI_TIMEOUT_SECONDS` | `60` | Tiempo máximo de una solicitud a OpenAI. |
| `OPENAI_MAX_RETRIES` | `2` | Reintentos ante fallos del proveedor. |
| `AGENT_MAX_TOOL_ROUNDS` | `5` | Máximo de rondas de herramientas por mensaje. |

### Búsqueda semántica

| Variable | Valor de ejemplo | Uso |
|---|---|---|
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo usado para generar embeddings. |
| `EMBEDDING_DIMENSIONS` | `1536` | Dimensión esperada por OpenAI, SQLAlchemy y pgvector. |
| `KNOWLEDGE_SCORE_THRESHOLD` | `0.30` | Similitud mínima para aceptar un fragmento. |
| `KNOWLEDGE_SCORE_MARGIN` | `0.10` | Distancia máxima permitida frente al mejor resultado. |

`EMBEDDING_DIMENSIONS` debe mantenerse en `1536` con el esquema actual. Cambiarlo exige modificar
la columna `kb_chunks.embedding` en `database/init.sql` y `KnowledgeChunkModel` antes de volver a
generar los vectores.

### Logs

| Variable | Valor predeterminado | Uso |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Nivel mínimo de registro. |
| `LOG_DIRECTORY` | `logs` | Directorio de salida. En Docker se usa `/app/logs`. |
| `LOG_FILENAME` | `app.log` | Nombre del archivo principal. |
| `LOG_MAX_BYTES` | `5000000` | Tamaño máximo antes de rotar el archivo. |
| `LOG_BACKUP_COUNT` | `5` | Cantidad de archivos históricos. |

## Ejecución con Docker

Esta es la opción recomendada para levantar el entorno completo:

```bash
docker compose up --build
```

El arranque sigue este orden:

1. PostgreSQL crea el esquema y carga los datos iniciales.
2. Redis queda disponible para las sesiones.
3. `knowledge-ingestion` genera los embeddings que estén pendientes.
4. FastAPI inicia cuando la base de datos y la indexación están listas.
5. Streamlit inicia cuando la API responde correctamente.

Servicios disponibles:

| Servicio | URL o puerto |
|---|---|
| Frontend Streamlit | http://localhost:8501 |
| API FastAPI | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |

Para ejecutar en segundo plano:

```bash
docker compose up --build -d
```

Para revisar logs:

```bash
docker compose logs -f app
docker compose logs -f knowledge-ingestion
```

Para detener los servicios sin borrar datos:

```bash
docker compose down
```

El archivo `database/init.sql` solo se ejecuta cuando PostgreSQL crea el volumen por primera vez.
Si el esquema cambió y necesitas reconstruir la base local desde cero:

```bash
docker compose down -v
docker compose up --build
```

El primer comando elimina la base de datos y las sesiones locales. No debe usarse si necesitas
conservar esa información.

## Ejecución para desarrollo local

Este modo ejecuta FastAPI y Streamlit en la máquina, pero mantiene PostgreSQL y Redis en Docker.

1. Instala las dependencias:

   ```bash
   uv sync
   ```

2. Inicia PostgreSQL y Redis:

   ```bash
   docker compose up -d db redis
   ```

3. Genera los embeddings pendientes:

   ```bash
   uv run python -m app.scripts.ingest_knowledge
   ```

4. Inicia la API:

   ```bash
   uv run uvicorn app.main:app --reload
   ```

5. En otra terminal, inicia el frontend:

   ```bash
   uv run streamlit run frontend/streamlit_app.py
   ```

La API necesita Redis desde el arranque. El endpoint `/chat` también requiere PostgreSQL, una API
key válida y que los fragmentos de conocimiento tengan embeddings cuando se consulte el RAG.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Información básica del servicio. |
| `GET` | `/health` | Verificación de disponibilidad de la API. |
| `GET` | `/health_database` | Verificación de la conexión con PostgreSQL. |
| `POST` | `/chat` | Envía un mensaje al agente. |
| `GET` | `/docs` | Documentación interactiva de FastAPI. |

### Enviar el primer mensaje

El `session_id` es opcional. Si no se envía, la API genera uno:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Busco un portátil para diseño gráfico por menos de 5 millones"
  }'
```

Respuesta esperada:

```json
{
  "session_id": "3a38a55e-a9ad-4d58-86a7-63b106a62e8c",
  "reply": "..."
}
```

### Continuar una conversación

Usa el mismo `session_id` en los mensajes siguientes:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "3a38a55e-a9ad-4d58-86a7-63b106a62e8c",
    "message": "Compara las dos mejores opciones"
  }'
```

La sesión conserva el historial, el cliente verificado, acciones pendientes y datos parciales de
garantías. Su duración depende de `REDIS_SESSION_TTL_SECONDS`.

## Flujos que se pueden probar

### Catálogo

No requiere identificación:

```text
Busco un portátil para diseño gráfico, con 16 GB de RAM y presupuesto de 5 millones.
```

El agente consulta el catálogo y puede comparar los SKU encontrados. No debe inventar precios,
existencias ni especificaciones.

### Pedidos

```text
Quiero consultar el pedido ORD-1001.
```

El agente solicitará la identificación porque los pedidos son información privada. Para este caso
puedes usar el cliente de prueba `1020304050`.

La dirección solo puede modificarse cuando el pedido está `CONFIRMED` o `PREPARING`. Por ejemplo,
el pedido `ORD-1010`, asociado al cliente `33445566`, permite probar ese flujo.

### Garantías y reclamos

```text
Quiero revisar la garantía del pedido ORD-1002.
```

Usa la identificación `987654321`. Ese pedido tiene más de un producto con garantía, por lo que el
agente debe pedir el SKU antes de continuar.

El flujo completo es:

1. Verificar al cliente.
2. Consultar la garantía por pedido y producto.
3. Confirmar que la cobertura esté vigente.
4. Solicitar una descripción concreta de la falla.
5. Crear o recuperar el ticket.
6. Escalarlo si existe una razón válida para atención humana.

### Atención humana general

```text
Quiero hablar con un asesor.
```

Este flujo no exige identificación. La solicitud se asocia a la sesión y, si ya existe una
solicitud activa para esa sesión, se devuelve la misma en lugar de crear un duplicado.

### Políticas y conocimiento

```text
¿Cuánto tarda un envío a una ciudad principal?
```

El agente consulta `kb_chunks` mediante búsqueda semántica. Si ningún fragmento supera el umbral
configurado, debe indicar que no tiene información oficial suficiente.

## Datos iniciales

`database/init.sql` carga un conjunto de datos para desarrollo:

- 54 productos de categorías como portátiles, televisores, celulares, accesorios, audio y gaming.
- 10 clientes.
- 15 pedidos con estados variados.
- Líneas de pedido con cantidades y precios históricos.
- 12 garantías vigentes y vencidas.
- 5 reclamos de garantía en diferentes estados.
- Fragmentos iniciales de políticas y preguntas frecuentes.

Algunos casos útiles:

| Identificación | Pedido | Caso |
|---|---|---|
| `1020304050` | `ORD-1001` | Pedido en tránsito y garantía vigente. |
| `987654321` | `ORD-1002` | Pedido entregado con dos productos cubiertos. |
| `33445566` | `ORD-1010` | Pedido en preparación; permite cambiar dirección. |
| `77889900` | `ORD-1011` | Garantía vencida. |
| `11223344` | `ORD-1007` | Reclamo previamente escalado. |

Todos estos datos son ficticios y solo se usan para pruebas.

## Modelo de datos

El modelo completo, con tipos y campos, está en
[`modelado_datos/model_datos.mmd`](modelado_datos/model_datos.mmd).

```mermaid
erDiagram
    CUSTOMERS ||--o{ ORDERS : realiza
    ORDERS ||--o{ ORDER_ITEMS : contiene
    PRODUCTS ||--o{ ORDER_ITEMS : aparece_en
    ORDERS ||--o{ WARRANTIES : genera
    PRODUCTS ||--o{ WARRANTIES : cubre
    WARRANTIES ||--o{ WARRANTY_CLAIMS : recibe
    CUSTOMERS ||--o{ WARRANTY_CLAIMS : reporta
    CUSTOMERS o|--o{ HUMAN_HANDOFFS : puede_asociarse
```

Consideraciones importantes:

- `order_items` resuelve la relación muchos a muchos entre pedidos y productos y conserva el
  precio unitario de la compra.
- Una garantía identifica el pedido y el producto cubierto. La combinación es única.
- Un reclamo pertenece a una garantía y a un cliente; su `id` también funciona como número de
  ticket.
- `human_handoffs.customer_id` es opcional porque una persona puede pedir un asesor antes de
  identificarse.
- Solo puede existir un handoff activo (`PENDING` o `ASSIGNED`) por sesión.
- `human_handoffs.session_id` apunta de forma lógica a la conversación de Redis; no es una clave
  foránea porque las sesiones no viven en PostgreSQL.
- `kb_chunks` es independiente del modelo transaccional y almacena un vector de 1536 dimensiones.

## Base de conocimiento y embeddings

Los fragmentos iniciales se insertan en `kb_chunks` desde `database/init.sql`. El comando de
ingesta no vuelve a leer automáticamente todos los archivos de `knowledge/`; su función es buscar
filas cuyo `embedding` sea `NULL`, generar el vector y guardarlo.

```bash
uv run python -m app.scripts.ingest_knowledge --batch-size 50
```

El proceso es idempotente para fragmentos ya vectorizados. Si se modifica el contenido de una fila
existente y se necesita regenerar su embedding, primero debe dejarse su columna `embedding` en
`NULL`.

El índice HNSW está documentado, pero no se crea por defecto porque el volumen de datos de prueba es
pequeño. Para una base de conocimiento mayor debe habilitarse después de cargar los embeddings.

## Reglas de seguridad del agente

- Las herramientas de pedidos y garantías toman la identificación desde la sesión verificada, no
  desde argumentos generados libremente por el modelo.
- Un pedido, garantía o ticket se consulta junto con el cliente para no revelar datos ajenos.
- El agente no expone teléfonos ni correos almacenados.
- La búsqueda de conocimiento no debe recibir datos personales.
- Los resultados de herramientas son la fuente de verdad para precios, inventario, pedidos,
  coberturas y políticas.
- La atención humana general puede solicitarse sin identificar al cliente.

Esta validación es adecuada para la prueba técnica, pero no reemplaza autenticación real,
autorización, auditoría ni cifrado de secretos en un entorno productivo.

## Pruebas y calidad

Ejecuta las pruebas:

```bash
uv run pytest
```

Revisa formato e importaciones:

```bash
uv run ruff check .
```

Ejecuta el análisis de tipos:

```bash
uv run pyrefly check
```

También se puede ejecutar la configuración completa de pre-commit:

```bash
uv run pre-commit run --all-files
```

## Solución de problemas

### La API no inicia y muestra un error de Redis

La aplicación valida Redis durante el arranque:

```bash
docker compose up -d redis
```

Comprueba también que `REDIS_URL` use `localhost` al ejecutar Python localmente y `redis` cuando la
aplicación se ejecuta dentro de Docker.

### Docker no inicia `app`

Revisa primero la ingesta:

```bash
docker compose logs knowledge-ingestion
```

En el primer arranque se necesita `OPENAI_API_KEY` para generar los embeddings. El servicio `app`
espera que `knowledge-ingestion` termine correctamente.

### El esquema nuevo no aparece en PostgreSQL

`database/init.sql` no modifica automáticamente un volumen existente. En un entorno local que pueda
reiniciarse:

```bash
docker compose down -v
docker compose up --build
```

### La búsqueda semántica falla por dimensiones

Verifica que `EMBEDDING_DIMENSIONS=1536`. La configuración, el modelo ORM y la columna pgvector
deben usar la misma dimensión.

### El chat pierde el contexto

Confirma que el frontend reutiliza el mismo `session_id` y que la sesión todavía existe en Redis.
Una sesión expira después del tiempo definido en `REDIS_SESSION_TTL_SECONDS`.

## Estado actual y límites conocidos

- El esquema se administra con `database/init.sql`. Alembic está incluido como dependencia, pero
  todavía no tiene migraciones configuradas.
- Los handoffs pueden crearse y consultarse como solicitud activa, pero aún no existe una API
  administrativa para asignarlos o cerrarlos.
- La interfaz conserva el identificador de sesión en la URL, pero no reconstruye visualmente los
  mensajes anteriores al abrirla en otro navegador.
- El chat y la indexación dependen de OpenAI; no existe un proveedor local alternativo configurado.
- El proyecto está preparado como prueba técnica. Antes de producción se deben agregar
  autenticación, gestión segura de secretos, migraciones, observabilidad y pruebas de integración.
