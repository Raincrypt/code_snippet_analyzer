"""The seam where an AI model plugs in.

The API only talks to the `Reviewer` protocol below. Today the only implementation is
`StubReviewer`, which returns a clearly-labelled placeholder so the whole app works end to end.

To add a real model later:
  1. Write a class (e.g. `LLMReviewer`) with the same two async methods and a `name`.
  2. Add its name to `Settings.reviewer` in app/config.py.
  3. Return it from `build_reviewer` below.
Nothing else in the API, database or tests has to change.
"""

from dataclasses import dataclass
from typing import Protocol

from app.config import Settings
from app.schemas import CodeIssue, Language, ReplyStyle, ReviewResult, Role


class ReviewerError(Exception):
    """Raise from a Reviewer when the review or answer cannot be produced (the API returns 502)."""


@dataclass(frozen=True)
class ReviewOutcome:
    result: ReviewResult
    # Metadata a real model fills in; stored with the review for cost and quality tracking.
    model: str | None = None
    prompt_version: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


@dataclass(frozen=True)
class ChatTurn:
    role: Role
    content: str


@dataclass(frozen=True)
class AnswerRequest:
    """Everything a model needs to answer a follow-up question about a review."""

    code: str
    language: Language
    review: ReviewResult
    history: tuple[ChatTurn, ...]
    question: str
    reply_style: ReplyStyle


@dataclass(frozen=True)
class AnswerOutcome:
    content: str
    model: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class Reviewer(Protocol):
    name: str

    async def review(self, code: str, language: Language) -> ReviewOutcome: ...

    async def answer(self, request: AnswerRequest) -> AnswerOutcome: ...


class StubReviewer:
    """Placeholder used until an AI model is connected. It never inspects the code."""

    name = "stub"

    async def review(self, code: str, language: Language) -> ReviewOutcome:
        result = ReviewResult(
            summary=(
                "This is a placeholder review. No AI reviewer is connected yet, "
                "so your code was not analysed."
            ),
            score=5,
            issues=[
                CodeIssue(
                    line=1,
                    severity="info",
                    category="best-practice",
                    title="No AI reviewer connected",
                    description=(
                        f"The backend received your {language} code "
                        f"({len(code.splitlines())} lines) and stored it, but a real review "
                        "needs an AI model. Connect one by adding a Reviewer implementation."
                    ),
                )
            ],
            positives=[],
        )
        return ReviewOutcome(result=result)

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        return AnswerOutcome(
            content=(
                f"(Placeholder reply, {request.reply_style} style.) No AI model is connected yet, "
                "so I can't answer questions about this code."
            )
        )


def build_reviewer(settings: Settings) -> Reviewer:
    if settings.reviewer == "stub":
        return StubReviewer()
    raise ValueError(f"Unknown reviewer: {settings.reviewer}")  # pragma: no cover
