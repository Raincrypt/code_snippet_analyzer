import asyncio
import json
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from app import sse
from app.models import Review
from app.schemas import REVIEW_STAGES, Language, ReviewCreate
from app.services.demo import DEMO_DIR
from app.services.review_stream import stream_review
from app.services.reviewer import (
    AnswerOutcome,
    AnswerRequest,
    ProgressCallback,
    ReviewerError,
    ReviewOutcome,
    StubReviewer,
)


def parse_events(text: str) -> list[tuple[str, Any]]:
    """Turn the raw text of an event stream into (event, data) pairs, skipping comments."""
    events = []
    for block in text.strip().split("\n\n"):
        if not block or block.startswith(":"):
            continue
        event_line, data_line = block.split("\n")
        events.append(
            (event_line.removeprefix("event: "), json.loads(data_line.removeprefix("data: ")))
        )
    return events


async def saved_count(app: FastAPI) -> int:
    async with app.state.session_factory() as session:
        return await session.scalar(select(func.count()).select_from(Review)) or 0


class SlowReviewer:
    name = "slow"

    def __init__(self, seconds: float = 10) -> None:
        self.seconds = seconds
        self.cancelled = False

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome:
        if progress:
            await progress("prepare")
        try:
            await asyncio.sleep(self.seconds)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return await StubReviewer().review(code, language)

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        return AnswerOutcome(content="")


class FailingReviewer(SlowReviewer):
    name = "failing"

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome:
        if progress:
            await progress("prepare")
        raise ReviewerError("provider timed out: secret detail")


class CrashingReviewer(SlowReviewer):
    name = "crashing"

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome:
        raise RuntimeError("boom: internal detail")


async def test_a_review_streams_every_step_then_the_saved_result(client: AsyncClient) -> None:
    response = await client.post(
        "/api/reviews/stream", json={"code": "print(1)", "language": "python"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"

    events = parse_events(response.text)
    assert [name for name, _ in events[:-1]] == ["stage"] * len(REVIEW_STAGES)
    assert [data["stage"] for _, data in events[:-1]] == list(REVIEW_STAGES)
    name, detail = events[-1]
    assert name == "result"
    assert detail["language"] == "python"
    assert detail["result"]["verdict"] == "not-assessed"


async def test_the_streamed_result_is_saved_and_can_be_read_back(client: AsyncClient) -> None:
    response = await client.post(
        "/api/reviews/stream", json={"code": "x = 1", "language": "python"}
    )
    detail = parse_events(response.text)[-1][1]
    fetched = await client.get(f"/api/reviews/{detail['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == detail["id"]


async def test_the_sample_code_gets_the_example_review_over_a_stream(client: AsyncClient) -> None:
    sample = (DEMO_DIR / "sample-code.txt").read_text(encoding="utf-8")
    response = await client.post(
        "/api/reviews/stream", json={"code": sample, "language": "javascript"}
    )
    result = parse_events(response.text)[-1][1]["result"]
    assert result["verdict"] == "needs-work"
    assert result["complexity"]["time"] == "O(n²)"


async def test_the_streamed_result_can_be_chatted_about(client: AsyncClient) -> None:
    response = await client.post("/api/reviews/stream", json={"code": "x", "language": "go"})
    review_id = parse_events(response.text)[-1][1]["id"]
    reply = await client.post(f"/api/reviews/{review_id}/messages", json={"question": "Why?"})
    assert reply.status_code == 201


async def test_a_bad_request_is_an_ordinary_error_not_a_stream(client: AsyncClient) -> None:
    blank = await client.post("/api/reviews/stream", json={"code": "  ", "language": "python"})
    assert blank.status_code == 422
    assert blank.headers["content-type"].startswith("application/json")
    assert blank.json()["error"]["code"] == "validation_error"


async def test_oversized_code_is_refused_before_streaming(
    client: AsyncClient,
    settings,  # type: ignore[no-untyped-def]
) -> None:
    too_long = "x" * (settings.max_code_chars + 1)
    response = await client.post(
        "/api/reviews/stream", json={"code": too_long, "language": "python"}
    )
    assert response.status_code == 413


async def test_a_reviewer_failure_arrives_as_an_error_event_and_saves_nothing(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.reviewer = FailingReviewer()
    response = await client.post(
        "/api/reviews/stream",
        json={"code": "x", "language": "python"},
        headers={"X-Request-ID": "trace-77"},
    )
    assert response.status_code == 200  # the stream had already started
    events = parse_events(response.text)
    assert [name for name, _ in events] == ["stage", "error"]
    error = events[-1][1]
    assert error["code"] == "reviewer_failed"
    assert error["requestId"] == "trace-77"
    assert "secret detail" not in response.text
    assert await saved_count(app) == 0


async def test_an_unexpected_crash_is_reported_without_internal_details(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.reviewer = CrashingReviewer()
    response = await client.post("/api/reviews/stream", json={"code": "x", "language": "python"})
    events = parse_events(response.text)
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "internal_error"
    assert "boom" not in response.text
    assert await saved_count(app) == 0


async def test_disconnecting_cancels_the_reviewer_and_saves_nothing(app: FastAPI) -> None:
    reviewer = SlowReviewer()
    events = stream_review(
        reviewer,
        app.state.session_factory,
        ReviewCreate(code="x", language="python"),
        request_id="r1",
    )
    first = await anext(events)
    assert first.startswith("event: stage")

    await events.aclose()  # what happens when the client goes away

    assert reviewer.cancelled
    assert await saved_count(app) == 0


async def test_quiet_periods_send_keep_alive_comments(app: FastAPI) -> None:
    reviewer = SlowReviewer(seconds=0.1)
    chunks = [
        chunk
        async for chunk in stream_review(
            reviewer,
            app.state.session_factory,
            ReviewCreate(code="x", language="python"),
            request_id="r1",
            keep_alive_seconds=0.02,
        )
    ]
    assert sse.KEEP_ALIVE in chunks
    assert chunks[-1].startswith("event: result")


async def test_the_stub_reports_each_step_in_order() -> None:
    seen: list[str] = []

    async def record(stage: str) -> None:
        seen.append(stage)

    await StubReviewer().review("x", "python", record)  # type: ignore[arg-type]
    assert seen == list(REVIEW_STAGES)


def test_events_are_single_line_json() -> None:
    assert sse.format_event("stage", {"stage": "prepare"}) == (
        'event: stage\ndata: {"stage":"prepare"}\n\n'
    )
    # A newline inside a value is escaped, so it cannot end the event early.
    assert "\n\n" not in sse.format_event("x", {"text": "a\n\nb"}).rstrip("\n")


def test_raw_events_refuse_multi_line_data() -> None:
    with pytest.raises(ValueError):
        sse.format_raw_event("result", '{"a":\n1}')
