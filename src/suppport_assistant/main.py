from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from suppport_assistant.core.config import settings
from suppport_assistant.core.errors import register_exception_handlers
from suppport_assistant.core.health import router as health_router
from suppport_assistant.core.logging import configure_logging
from suppport_assistant.core.middleware import RequestIDMiddleware
from suppport_assistant.core.ratelimit import limiter
from suppport_assistant.modules.auth.router import router as auth_router
from suppport_assistant.modules.conversations.router import (
    router as conversations_router,
)
from suppport_assistant.modules.knowledge_base.router import (
    router as knowledge_router,
)
from suppport_assistant.modules.tickets.router import router as tickets_router
from suppport_assistant.modules.users.router import router as users_router

OPENAPI_DESCRIPTION = """
AI customer-support API. Authenticated users chat with a RAG-powered support
assistant that answers from a pgvector-backed knowledge base, and manage support
tickets. Transactional email is sent via Resend.

Authenticate by calling `/api/v1/auth/login` and sending the returned access token
as `Authorization: Bearer <token>`.
"""

OPENAPI_TAGS = [
    {"name": "auth", "description": "Sign-up, login, tokens, verification, reset."},
    {"name": "users", "description": "Current user profile and password."},
    {"name": "tickets", "description": "Support tickets."},
    {"name": "conversations", "description": "Chat threads with the assistant."},
    {"name": "knowledge", "description": "Knowledge base ingestion and vector search."},
    {"name": "health", "description": "Liveness and readiness probes."},
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        description=OPENAPI_DESCRIPTION,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
    )

    app.state.limiter = limiter

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(users_router, prefix=settings.api_v1_prefix)
    app.include_router(tickets_router, prefix=settings.api_v1_prefix)
    app.include_router(conversations_router, prefix=settings.api_v1_prefix)
    app.include_router(knowledge_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "suppport_assistant.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
    )
