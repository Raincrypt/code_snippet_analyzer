"""Runs a review and reports it as a stream of Server-Sent Events.

Events, in order:
  stage   {"stage": "prepare"}      one per step, as the reviewer reports it
  result  <the saved review>        the review finished and was saved
  error   {"code", "message", "requestId"}   something went wrong (the stream then ends)

If the client disconnects, the reviewer task is cancelled, so an abandoned request stops costing
anything (important once the reviewer calls a paid or slow model).
"""

import asyncio
import contextlib
import logging
import time
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import repository, sse
from app.errors import ReviewerFailedError
from app.schemas import MessageOut, ReviewCreate, ReviewDetail, ReviewResult, ReviewStage
from app.services.reviewer import Reviewer, ReviewerError, ReviewOutcome

logger = logging.getLogger(__name__)

KEEP_ALIVE_SECONDS = 15.0


def to_detail(review: Any) -> ReviewDetail:
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


def _error_event(code: str, message: str, request_id: str | None) -> str:
    return sse.format_event("error", {"code": code, "message": message, "requestId": request_id})


async def stream_review(
    reviewer: Reviewer,
    session_factory: async_sessionmaker[AsyncSession],
    body: ReviewCreate,
    request_id: str | None,
    keep_alive_seconds: float = KEEP_ALIVE_SECONDS,
) -> AsyncIterator[str]:
    # Everything the reviewer task reports goes through this queue, so the generator below is the
    # only place that writes to the client.
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

    async def report(stage: ReviewStage) -> None:
        await queue.put(("stage", stage))

    async def run() -> None:
        try:
            outcome = await reviewer.review(body.code, body.language, report)
            await queue.put(("done", outcome))
        except ReviewerError as exc:
            logger.warning("Reviewer failed: %s", exc)
            await queue.put(("failed", exc))
        except Exception as exc:  # noqa: BLE001 - reported to the client as a generic error
            logger.exception("Unexpected reviewer error")
            await queue.put(("crashed", exc))

    started = time.perf_counter()
    task = asyncio.create_task(run())
    try:
        while True:
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=keep_alive_seconds)
            except TimeoutError:
                yield sse.KEEP_ALIVE
                continue

            if kind == "stage":
                yield sse.format_event("stage", {"stage": payload})
            elif kind == "done":
                outcome: ReviewOutcome = payload
                latency_ms = round((time.perf_counter() - started) * 1000)
                try:
                    async with session_factory() as session:
                        review = await repository.create_review(
                            session, body, reviewer.name, outcome, latency_ms
                        )
                        detail = to_detail(review)
                except Exception:  # noqa: BLE001
                    logger.exception("Could not save the review")
                    yield _error_event(
                        "internal_error", "The review could not be saved.", request_id
                    )
                    return
                yield sse.format_raw_event("result", detail.model_dump_json(by_alias=True))
                return
            elif kind == "failed":
                error = ReviewerFailedError(payload.public_message)
                yield _error_event(error.code, error.message, request_id)
                return
            else:
                yield _error_event(
                    "internal_error", "Something went wrong on our side.", request_id
                )
                return
    finally:
        # Reached on normal completion, on errors, and when the client disconnects.
        if not task.done():
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
