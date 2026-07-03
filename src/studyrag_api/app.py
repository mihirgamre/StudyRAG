from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy.engine import Engine

from studyrag_core import ConfidenceGate, HashingEmbeddingModel, OpenAIChatResponseGenerator
from studyrag_core.embeddings import EmbeddingModel
from studyrag_core.generation import ResponseGenerator
from studyrag_ingestion import storage_from_env
from studyrag_ingestion.storage import ObjectStorage
from studyrag_persistence.database import create_engine_from_url

from .auth import router as auth_router
from .conversations import router as conversations_router
from .courses import router as courses_router
from .documents import router as documents_router
from .rate_limit import limiter


def create_app(
    *,
    engine: Engine | None = None,
    storage: ObjectStorage | None = None,
    embedding_model: EmbeddingModel | None = None,
    confidence_gate: ConfidenceGate | None = None,
    response_generator: ResponseGenerator | None = None,
    jwt_secret: str | None = None,
    retrieval_top_k: int | None = None,
) -> FastAPI:
    app = FastAPI(title="StudyRAG API")
    app.state.engine = engine or create_engine_from_url()
    app.state.storage = storage or storage_from_env()
    app.state.embedding_model = embedding_model or HashingEmbeddingModel()
    app.state.confidence_gate = confidence_gate or ConfidenceGate()
    app.state.response_generator = response_generator if response_generator is not None else response_generator_from_env()
    app.state.jwt_secret = jwt_secret or os.getenv("JWT_SECRET", "dev-only-change-me-use-env-in-production")
    app.state.retrieval_top_k = retrieval_top_k or int(os.getenv("STUDYRAG_RETRIEVAL_TOP_K", "4"))
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins_from_env(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(courses_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def cors_origins_from_env() -> list[str]:
    raw_origins = os.getenv("STUDYRAG_CORS_ORIGINS") or os.getenv("FRONTEND_ORIGIN")
    if raw_origins:
        return [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def response_generator_from_env() -> ResponseGenerator | None:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("LLM_MODEL")
    if not api_key:
        return None
    if not model:
        raise RuntimeError("LLM_MODEL is required when LLM_API_KEY or OPENAI_API_KEY is set")
    return OpenAIChatResponseGenerator(
        api_key=api_key,
        model=model,
        base_url=os.getenv("LLM_BASE_URL") or None,
    )
