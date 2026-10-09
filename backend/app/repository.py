"""All database reads and writes for reviews and messages."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Review
from app.schemas import MessageCreate, ReviewCreate
from app.services.reviewer import AnswerOutcome, ReviewOutcome


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
