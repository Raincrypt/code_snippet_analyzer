"""Proves a different Reviewer (e.g. a future LLM one) can be dropped in without API changes."""

from fastapi import FastAPI
from httpx import AsyncClient

from app.schemas import CodeIssue, Language, ReviewResult
from app.services.reviewer import AnswerOutcome, AnswerRequest, ReviewerError, ReviewOutcome


class FakeModelReviewer:
    name = "fake-model"

    async def review(self, code: str, language: Language) -> ReviewOutcome:
        result = ReviewResult(
            summary="Found one problem.",
            score=3,
            issues=[
                CodeIssue(
                    line=2, severity="error", category="bug", title="Bad", description="Because."
                )
            ],
            positives=[],
        )
        return ReviewOutcome(
            result=result, model="fake-1", prompt_version="v1", tokens_in=120, tokens_out=45
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
    assert (await client.get("/api/reviews")).json()["total"] == 0
