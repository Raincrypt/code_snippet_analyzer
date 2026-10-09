"""Proves a different Reviewer (e.g. a future LLM one) can be dropped in without API changes."""

from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models import Review
from app.schemas import (
    AreaScore,
    CodeIssue,
    Language,
    Metrics,
    ReviewResult,
    ScoreBreakdown,
)
from app.services.reviewer import AnswerOutcome, AnswerRequest, ReviewerError, ReviewOutcome


def fake_result() -> ReviewResult:
    return ReviewResult(
        purpose="Adds two numbers.",
        summary="Found one problem.",
        verdict="needs-work",
        score=3,
        score_breakdown=ScoreBreakdown(
            correctness=AreaScore(score=3, reason="Bad."),
            security=AreaScore(score=9, reason="Fine."),
            performance=AreaScore(score=8, reason="Fine."),
            readability=AreaScore(score=7, reason="Fine."),
        ),
        priority_fixes=["f1"],
        issues=[
            CodeIssue(
                id="f1",
                line=2,
                severity="error",
                category="bug",
                title="Bad",
                explanation="Because.",
                impact="It breaks.",
                evidence="x",
                confidence="high",
                effort="quick",
            )
        ],
        positives=[],
        metrics=Metrics(
            total_lines=1, code_lines=1, comment_lines=0, blank_lines=0, longest_line=1
        ),
    )


class FakeModelReviewer:
    name = "fake-model"

    async def review(self, code: str, language: Language) -> ReviewOutcome:
        return ReviewOutcome(
            result=fake_result(), model="fake-1", prompt_version="v1", tokens_in=120, tokens_out=45
        )

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        return AnswerOutcome(content=f"You asked: {request.question}")


class BrokenReviewer:
    name = "broken"

    async def review(self, code: str, language: Language) -> ReviewOutcome:
        raise ReviewerError("provider timed out")

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        raise ReviewerError("provider timed out")


async def test_reviewer_metadata_is_stored(app: FastAPI, client: AsyncClient) -> None:
    app.state.reviewer = FakeModelReviewer()
    body = (await client.post("/api/reviews", json={"code": "x", "language": "python"})).json()
    assert body["reviewer"] == "fake-model"
    assert body["model"] == "fake-1"
    assert body["promptVersion"] == "v1"
    assert (body["tokensIn"], body["tokensOut"]) == (120, 45)
    assert body["latencyMs"] is not None
    assert body["result"]["issues"][0]["title"] == "Bad"


async def test_follow_up_questions_go_through_the_reviewer(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.reviewer = FakeModelReviewer()
    review = (await client.post("/api/reviews", json={"code": "x", "language": "go"})).json()
    reply = await client.post(f"/api/reviews/{review['id']}/messages", json={"question": "Hm?"})
    assert reply.json()["assistantMessage"]["content"] == "You asked: Hm?"


async def test_reviewer_failure_becomes_a_502_and_saves_nothing(
    app: FastAPI, client: AsyncClient
) -> None:
    app.state.reviewer = BrokenReviewer()
    response = await client.post("/api/reviews", json={"code": "x", "language": "python"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "reviewer_failed"
    assert "timed out" not in response.text  # internal details are not leaked
    async with app.state.session_factory() as session:
        saved = await session.scalar(select(func.count()).select_from(Review))
    assert saved == 0
