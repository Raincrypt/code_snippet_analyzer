"""The seam where an AI model plugs in.

The API only talks to the `Reviewer` protocol below. Today the only implementation is
`StubReviewer`, a placeholder so the whole app works end to end.

To add a real model later:
  1. Write a class (e.g. `LLMReviewer`) with the same two async methods and a `name`.
  2. Add its name to `Settings.reviewer` in app/config.py.
  3. Return it from `build_reviewer` below.
Nothing else in the API, database or tests has to change.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import Settings
from app.schemas import REVIEW_STAGES, Language, ReplyStyle, ReviewResult, ReviewStage, Role
from app.services.demo import demo_review_for
from app.services.metrics import measure

# Called as each step of a review begins, so the UI can show progress.
ProgressCallback = Callable[[ReviewStage], Awaitable[None]]


class ReviewerError(Exception):
    """Raise from a Reviewer when the review or answer cannot be produced (the API returns 502).

    `public_message` is what the user is told. The exception's own text is only for the logs,
    because it may contain internal details.
    """

    public_message = "The reviewer could not complete the review."


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

    # The model behind the reviewer, if any (shown in the UI). None for the placeholder.
    @property
    def model_name(self) -> str | None: ...

    async def check(self) -> dict[str, Any]:
        """Whether the reviewer can work right now (for the status endpoint)."""
        ...

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome: ...

    async def answer(self, request: AnswerRequest) -> AnswerOutcome: ...


class StubReviewer:
    """Placeholder used until an AI model is connected.

    It does not analyse code. For the built-in sample it returns a canned example review so the
    interface can be demonstrated; for anything else it says plainly that nothing was analysed.
    """

    name = "stub"
    model_name: str | None = None

    async def check(self) -> dict[str, Any]:
        return {
            "ready": True,
            "state": "ready",
            "model": None,
            "detail": "Placeholder reviewer; no model needed.",
        }

    def __init__(self, step_delay_seconds: float = 0.0) -> None:
        self.step_delay_seconds = step_delay_seconds

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome:
        # Reports every step so the streaming path works end to end; nothing real happens in them.
        for stage in REVIEW_STAGES:
            if progress is not None:
                await progress(stage)
            if self.step_delay_seconds:
                await asyncio.sleep(self.step_delay_seconds)
        demo = demo_review_for(code)
        if demo is not None:
            return ReviewOutcome(result=demo)
        return ReviewOutcome(result=self._not_assessed(code))

    @staticmethod
    def _not_assessed(code: str) -> ReviewResult:
        return ReviewResult(
            purpose="Not analysed.",
            summary=(
                "This is a placeholder. No AI reviewer is connected yet, so your code was not "
                "analysed. The measurements shown are taken directly from your code."
            ),
            verdict="not-assessed",
            priority_fixes=[],
            issues=[],
            positives=[],
            metrics=measure(code),
            limitations=["No AI reviewer is connected, so no findings, complexity or score."],
        )

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        return AnswerOutcome(
            content=(
                f"(Placeholder reply, {request.reply_style} style.) No AI model is connected yet, "
                "so I can't answer questions about this code."
            )
        )


def build_reviewer(settings: Settings) -> Reviewer:
    if settings.reviewer == "stub":
        return StubReviewer(step_delay_seconds=settings.stub_step_delay_seconds)
    if settings.reviewer == "llm":
        from app.services.llm_reviewer import build_llm_reviewer  # imported here: it imports us

        return build_llm_reviewer(settings)
    raise ValueError(f"Unknown reviewer: {settings.reviewer}")  # pragma: no cover
