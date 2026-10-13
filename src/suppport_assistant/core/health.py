from fastapi import APIRouter
from sqlalchemy import text

from suppport_assistant.core.errors import ServiceUnavailableError
from suppport_assistant.db.session import SessionDep

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe (checks the database)")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await session.exec(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailableError("Database is unavailable") from exc
    return {"status": "ready"}
