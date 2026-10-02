from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.api.deps import ReviewerDep, SessionDep
from app.errors import NotReadyError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(reviewer: ReviewerDep) -> dict[str, Any]:
    """Liveness: the process is up. Does not touch the database."""
    return {"status": "ok", "version": __version__, "reviewer": reviewer.name}


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    """Readiness: the app can serve traffic, i.e. the database answers."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise NotReadyError("The database is not reachable.") from exc
    return {"status": "ready"}
