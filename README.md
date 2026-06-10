# Retail AI Agent

Base project for a FastAPI retail assistant using clean architecture, PostgreSQL, pgvector, RAG,
and OpenAI.

## Local development

```bash
uv sync
uv run uvicorn app.main:app --reload
```

The liveness endpoint is available at `GET /health`. The current `POST /chat` route is a scaffold
and will be connected to `AgentService` in a later phase.

## Streamlit frontend

Start FastAPI in one terminal:

```bash
uv run uvicorn app.main:app --reload
```

Start Streamlit in another terminal:

```bash
uv run streamlit run frontend/streamlit_app.py
```

The frontend uses `http://localhost:8000` by default. Set `API_BASE_URL` to use another API URL.

## Docker

```bash
docker compose up --build
```

Configuration variables are documented in `.env.example`.
