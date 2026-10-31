"""The llm reviewer working through the real API (the model itself is faked)."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app
from app.models import Base
from app.services.llm_client import LlmBadReplyError
from app.services.llm_reviewer import LlmReviewer
from tests.llm_fakes import CODE, FakeClient, as_text, good_reply


@pytest.fixture
def fake() -> FakeClient:
    return FakeClient()


@pytest.fixture
async def llm_client(fake: FakeClient) -> AsyncIterator[AsyncClient]:
    settings = Settings(
        environment="test",
        log_level="WARNING",
        database_url="sqlite+aiosqlite:///:memory:",
        reviewer="llm",
        llm_max_code_chars=1000,
    )
    app: FastAPI = create_app(settings)
    app.state.reviewer = LlmReviewer(fake)  # swap the real HTTP client for the fake
    async with app.router.lifespan_context(app):
        async with app.state.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as http:
            yield http


async def test_health_and_status_show_the_model(llm_client: AsyncClient) -> None:
    health = (await llm_client.get("/api/health")).json()
    assert health["reviewer"] == "llm" and health["model"] == "fake-model"
    status = (await llm_client.get("/api/reviewer/status")).json()
    assert status["ready"] is True and status["model"] == "fake-model"


async def test_review_is_saved_with_model_metadata(
    llm_client: AsyncClient, fake: FakeClient
) -> None:
    fake.replies.append(as_text(good_reply()))
    response = await llm_client.post("/api/reviews", json={"code": CODE, "language": "python"})
    assert response.status_code == 201
    body = response.json()
    assert body["reviewer"] == "llm" and body["model"] == "fake-model"
    assert body["promptVersion"] == "review_v2"
    assert (body["tokensIn"], body["tokensOut"]) == (100, 50)
    assert body["result"]["issues"][0]["id"] == "I1"
    assert body["result"]["complexity"]["time"] == "O(n)"


async def test_streamed_review_reports_stages(llm_client: AsyncClient, fake: FakeClient) -> None:
    fake.replies.append(as_text(good_reply()))
    response = await llm_client.post(
        "/api/reviews/stream", json={"code": CODE, "language": "python"}
    )
    text = response.text
    order = [text.index(f'"stage":"{s}"') for s in ("prepare", "understand", "analyse", "verify")]
    assert order == sorted(order)
    assert "event: result" in text


async def test_model_failure_becomes_a_clean_error_event(
    llm_client: AsyncClient, fake: FakeClient
) -> None:
    fake.replies.append(LlmBadReplyError("secret internal detail"))
    response = await llm_client.post(
        "/api/reviews/stream", json={"code": CODE, "language": "python"}
    )
    assert "event: error" in response.text
    assert "secret internal detail" not in response.text


async def test_snippet_over_the_model_limit_is_rejected(llm_client: AsyncClient) -> None:
    response = await llm_client.post(
        "/api/reviews", json={"code": "x = 1\n" * 300, "language": "python"}
    )
    assert response.status_code == 413
    assert "1000" in response.json()["error"]["message"]


async def test_chat_answer_comes_from_the_model(llm_client: AsyncClient, fake: FakeClient) -> None:
    fake.replies.extend([as_text(good_reply()), "Add a guard clause."])
    review = (
        await llm_client.post("/api/reviews", json={"code": CODE, "language": "python"})
    ).json()
    response = await llm_client.post(
        f"/api/reviews/{review['id']}/messages", json={"question": "How to fix?"}
    )
    assert response.status_code == 201
    assert response.json()["assistantMessage"]["content"] == "Add a guard clause."


async def test_users_are_told_a_safe_reason(llm_client: AsyncClient, fake: FakeClient) -> None:
    from app.services.llm_client import LlmTimeoutError, LlmUnavailableError

    fake.replies.append(LlmUnavailableError("connect to 10.0.0.5:11434 refused"))
    down = await llm_client.post("/api/reviews", json={"code": CODE, "language": "python"})
    assert down.status_code == 502
    assert "not available" in down.json()["error"]["message"]
    assert "10.0.0.5" not in down.text

    fake.replies.append(LlmTimeoutError("read timeout"))
    slow = await llm_client.post("/api/reviews/stream", json={"code": CODE, "language": "python"})
    assert "took too long" in slow.text
