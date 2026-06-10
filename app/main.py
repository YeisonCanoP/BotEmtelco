from fastapi import FastAPI

from app.interfaces.api.routes.routers import api_router

app = FastAPI(
    title="Agente de prueba Tecnica Emtelco",
    version="0.1.0",
)

app.include_router(api_router)
