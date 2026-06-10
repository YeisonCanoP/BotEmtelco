from fastapi import FastAPI

from app.interfaces.api.routes.chat import router as chat_router
from app.interfaces.api.routes.health import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(title="Retail AI Agent", version="0.1.0")
    application.include_router(health_router)
    application.include_router(chat_router)
    return application


app = create_app()
