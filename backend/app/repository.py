"""All database reads and writes for reviews and messages."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Review
from app.schemas import MessageCreate, ReviewCreate
from app.services.reviewer import AnswerOutcome, ReviewOutcome

PREVIEW_CHARS = 120


async def create_review(
    session: AsyncSession,
    data: ReviewCreate,
    reviewer_name: str,
    outcome: ReviewOutcome,
    latency_ms: int,
) -> Review:
    review = Review(
        language=data.language,
        code=data.code,
        # Stored in the same camelCase shape the API returns.
        result=outcome.result.model_dump(mode="json", by_alias=True),
        reviewer=reviewer_name,
        model=outcome.model,
        prompt_version=outcome.prompt_version,
        tokens_in=outcome.tokens_in,
        tokens_out=outcome.tokens_out,
        latency_ms=latency_ms,
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def get_review(session: AsyncSession, review_id: uuid.UUID) -> Review | None:
    return await session.get(Review, review_id)


async def list_reviews(
    session: AsyncSession, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    """Newest first. Loads only the columns the list needs, not the full code."""
    total = await session.scalar(select(func.count()).select_from(Review)) or 0
    rows = await session.execute(
        select(
            Review.id,
            Review.language,
            Review.result,
            Review.created_at,
            func.substr(Review.code, 1, PREVIEW_CHARS).label("preview"),
        )
        .order_by(Review.created_at.desc(), Review.id)
        .limit(limit)
        .offset(offset)
    )
    return [dict(row._mapping) for row in rows], total


async def delete_review(session: AsyncSession, review: Review) -> None:
    await session.delete(review)
    await session.commit()


async def add_exchange(
    session: AsyncSession,
    review: Review,
    data: MessageCreate,
    outcome: AnswerOutcome,
) -> tuple[Message, Message]:
    user = Message(review_id=review.id, role="user", content=data.question)
    assistant = Message(
        review_id=review.id,
        role="assistant",
        content=outcome.content,
        reply_style=data.reply_style,
    )
    session.add_all([user, assistant])
    await session.commit()
    await session.refresh(user)
    await session.refresh(assistant)
    return user, assistant
