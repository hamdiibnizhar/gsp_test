from __future__ import annotations

from fastapi import FastAPI

from src.api.openai_routes import router as openai_router
from src.api.routes import router
from src.config import AppConfig
from src.rag import RAGService


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig.from_env()
    app = FastAPI(title="Local Agentic RAG API", version="1.0.0")
    app.state.rag_service = RAGService(config=app_config)
    app.state.app_config = app_config
    app.include_router(router)
    app.include_router(openai_router)
    return app
