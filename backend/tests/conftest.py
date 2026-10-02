from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.models import Base

SAMPLE_CODE = "def add(a, b):\n    return a + b\n"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        log_level="WARNING",
        database_url="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    application = create_app(settings)
    # httpx does not run the app's startup/shutdown, so run it here.
    async with application.router.lifespan_context(application):
        async with application.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def review(client: AsyncClient) -> dict[str, object]:
    """A saved review, as returned by the API."""
    response = await client.post("/api/reviews", json={"code": SAMPLE_CODE, "language": "python"})
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]
