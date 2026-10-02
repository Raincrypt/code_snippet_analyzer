"""Request and response shapes. JSON uses camelCase, matching the frontend's Zod schemas."""

from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

Severity = Literal["error", "warning", "info", "suggestion"]
Category = Literal["bug", "security", "performance", "style", "best-practice"]
Language = Literal["javascript", "typescript", "python", "go", "rust", "java"]
ReplyStyle = Literal["brief", "balanced", "detailed"]
Role = Literal["user", "assistant"]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---- the review itself (the contract a future LLM must produce) -----------------------------


class CodeIssue(CamelModel):
    line: int = Field(ge=1)
    end_line: int | None = Field(default=None, ge=1)
    severity: Severity
    category: Category
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    suggestion: str | None = None

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_line is not None and self.end_line < self.line:
            raise ValueError("endLine must not be before line")
        return self


class Positive(CamelModel):
    line: int = Field(ge=1)
    comment: str


class ReviewResult(CamelModel):
    summary: str
    score: int = Field(ge=1, le=10)
    issues: list[CodeIssue]
    positives: list[Positive]


# ---- requests -------------------------------------------------------------------------------


class ReviewCreate(CamelModel):
    code: str
    language: Language

    @field_validator("code")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("code must not be empty")
        return value


class MessageCreate(CamelModel):
    question: str = Field(min_length=1)
    reply_style: ReplyStyle = "balanced"

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()


# ---- responses ------------------------------------------------------------------------------


class MessageOut(CamelModel):
    id: UUID
    role: Role
    content: str
    reply_style: ReplyStyle | None
    created_at: datetime


class MessageExchange(CamelModel):
    user_message: MessageOut
    assistant_message: MessageOut


class ReviewDetail(CamelModel):
    id: UUID
    language: Language
    code: str
    result: ReviewResult
    reviewer: str
    model: str | None
    prompt_version: str | None
    tokens_in: int | None
    tokens_out: int | None
    latency_ms: int | None
    created_at: datetime
    messages: list[MessageOut]


class ReviewSummary(CamelModel):
    id: UUID
    language: Language
    score: int
    issue_count: int
    preview: str
    created_at: datetime


class ReviewPage(CamelModel):
    items: list[ReviewSummary]
    total: int
    limit: int
    offset: int
