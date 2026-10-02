from collections.abc import AsyncIterator
from typing import Any

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool


def create_engine(database_url: str) -> AsyncEngine:
    kwargs: dict[str, Any] = {}
    is_sqlite = database_url.startswith("sqlite")
    if is_sqlite and ":memory:" in database_url:
        # An in-memory SQLite database is per-connection; share one connection (used by tests).
        kwargs = {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}

    engine = create_async_engine(database_url, **kwargs)

    if is_sqlite:

        @event.listens_for(engine.sync_engine, "connect")
        def enforce_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
            # SQLite ignores foreign keys unless asked; PostgreSQL always enforces them.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one database session per request."""
    async with request.app.state.session_factory() as session:
        yield session
