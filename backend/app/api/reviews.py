import time
import uuid

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app import repository
from app.api.deps import ReviewerDep, SessionDep, SettingsDep
from app.config import Settings
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
from app.services.review_stream import stream_review, to_detail
from app.services.reviewer import AnswerRequest, ChatTurn, ReviewerError

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def get_or_404(session: SessionDep, review_id: uuid.UUID) -> Review:
    review = await repository.get_review(session, review_id)
    if review is None:
        raise NotFoundError("Review not found.")
    return review


def check_code_size(code: str, settings: Settings) -> None:
    limit = settings.code_limit
    if len(code) > limit:
        raise PayloadTooLargeError(f"Code is too long (maximum {limit} characters).")


@router.post("/stream")
async def create_review_stream(
    body: ReviewCreate, request: Request, reviewer: ReviewerDep, settings: SettingsDep
) -> StreamingResponse:
    """Review a snippet, reporting each step as it happens (Server-Sent Events).

    Problems with the request itself (blank code, too long) are ordinary error responses.
    Problems during the review arrive as an `error` event, because the response has started.
    """
    check_code_size(body.code, settings)
    events = stream_review(
        reviewer,
        request.app.state.session_factory,
        body,
        getattr(request.state, "request_id", None),
    )
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        # no-cache and X-Accel-Buffering stop browsers and proxies (nginx) from holding events back.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=ReviewDetail, status_code=201)
async def create_review(
    body: ReviewCreate, session: SessionDep, reviewer: ReviewerDep, settings: SettingsDep
) -> ReviewDetail:
    """Review a snippet and save the result, without progress reporting."""
    check_code_size(body.code, settings)

    started = time.perf_counter()
    try:
        outcome = await reviewer.review(body.code, body.language)
    except ReviewerError as exc:
        raise ReviewerFailedError(exc.public_message) from exc
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
        message = (
            exc.public_message
            if type(exc) is not ReviewerError
            else "The reviewer could not answer."
        )
        raise ReviewerFailedError(message) from exc

    user, assistant = await repository.add_exchange(session, review, body, outcome)
    return MessageExchange(
        user_message=MessageOut.model_validate(user),
        assistant_message=MessageOut.model_validate(assistant),
    )
