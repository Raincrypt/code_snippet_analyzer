import time
import uuid

from fastapi import APIRouter

from app import repository
from app.api.deps import ReviewerDep, SessionDep, SettingsDep
from app.errors import NotFoundError, PayloadTooLargeError, ReviewerFailedError
from app.models import Review
from app.schemas import (
    MessageCreate,
    MessageExchange,
    MessageOut,
    ReviewCreate,
    ReviewDetail,
    ReviewResult,
)
from app.services.reviewer import AnswerRequest, ChatTurn, ReviewerError

router = APIRouter(prefix="/reviews", tags=["reviews"])


def to_detail(review: Review) -> ReviewDetail:
    return ReviewDetail(
        id=review.id,
        language=review.language,
        code=review.code,
        result=ReviewResult.model_validate(review.result),
        reviewer=review.reviewer,
        model=review.model,
        prompt_version=review.prompt_version,
        tokens_in=review.tokens_in,
        tokens_out=review.tokens_out,
        latency_ms=review.latency_ms,
        created_at=review.created_at,
        messages=[MessageOut.model_validate(m) for m in review.messages],
    )


async def get_or_404(session: SessionDep, review_id: uuid.UUID) -> Review:
    review = await repository.get_review(session, review_id)
    if review is None:
        raise NotFoundError("Review not found.")
    return review


@router.post("", response_model=ReviewDetail, status_code=201)
async def create_review(
    body: ReviewCreate, session: SessionDep, reviewer: ReviewerDep, settings: SettingsDep
) -> ReviewDetail:
    """Review a snippet and save the result."""
    if len(body.code) > settings.max_code_chars:
        raise PayloadTooLargeError(
            f"Code is too long (maximum {settings.max_code_chars} characters)."
        )

    started = time.perf_counter()
    try:
        outcome = await reviewer.review(body.code, body.language)
    except ReviewerError as exc:
        raise ReviewerFailedError("The reviewer could not complete the review.") from exc
    latency_ms = round((time.perf_counter() - started) * 1000)

    review = await repository.create_review(session, body, reviewer.name, outcome, latency_ms)
    return to_detail(review)


@router.get("/{review_id}", response_model=ReviewDetail)
async def get_review(review_id: uuid.UUID, session: SessionDep) -> ReviewDetail:
    return to_detail(await get_or_404(session, review_id))


@router.post("/{review_id}/messages", response_model=MessageExchange, status_code=201)
async def ask_question(
    review_id: uuid.UUID,
    body: MessageCreate,
    session: SessionDep,
    reviewer: ReviewerDep,
    settings: SettingsDep,
) -> MessageExchange:
    """Ask a follow-up question about a review. Both messages are saved with the review."""
    if len(body.question) > settings.max_question_chars:
        raise PayloadTooLargeError(
            f"Question is too long (maximum {settings.max_question_chars} characters)."
        )
    review = await get_or_404(session, review_id)

    request = AnswerRequest(
        code=review.code,
        language=review.language,  # type: ignore[arg-type]
        review=ReviewResult.model_validate(review.result),
        history=tuple(ChatTurn(m.role, m.content) for m in review.messages),  # type: ignore[arg-type]
        question=body.question,
        reply_style=body.reply_style,
    )
    try:
        outcome = await reviewer.answer(request)
    except ReviewerError as exc:
        raise ReviewerFailedError("The reviewer could not answer.") from exc

    user, assistant = await repository.add_exchange(session, review, body, outcome)
    return MessageExchange(
        user_message=MessageOut.model_validate(user),
        assistant_message=MessageOut.model_validate(assistant),
    )
