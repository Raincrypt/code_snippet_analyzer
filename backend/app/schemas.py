"""Request and response shapes. JSON uses camelCase, matching the frontend's Zod schemas."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel

Severity = Literal["error", "warning", "info", "suggestion"]
Category = Literal["bug", "security", "performance", "style", "best-practice"]
Language = Literal["javascript", "typescript", "python", "go", "rust", "java"]
ReplyStyle = Literal["brief", "balanced", "detailed"]
Role = Literal["user", "assistant"]
Confidence = Literal["high", "medium", "low"]
Effort = Literal["quick", "moderate", "larger"]
# "not-assessed" is used by the placeholder reviewer, which does not look at the code.
Verdict = Literal["fix-before-use", "needs-work", "mostly-fine", "looks-good", "not-assessed"]

# Big-O notation such as O(1), O(n log n), O(n²), O(2^n), O(V + E).
BigO = Annotated[str, StringConstraints(pattern=r"^O\(.+\)$", max_length=40)]


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---- the review itself (the contract a future LLM must produce) -----------------------------


class Reference(CamelModel):
    label: str = Field(min_length=1, max_length=120)
    url: str | None = None


class Fix(CamelModel):
    description: str = Field(min_length=1)
    before: str | None = None
    after: str = Field(min_length=1)


class CodeIssue(CamelModel):
    id: str = Field(min_length=1, max_length=20)
    line: int = Field(ge=1)
    end_line: int | None = Field(default=None, ge=1)
    severity: Severity
    category: Category
    title: str = Field(min_length=1, max_length=120)
    explanation: str = Field(min_length=1)  # what is wrong
    impact: str = Field(min_length=1)  # why it matters
    evidence: str = Field(min_length=1)  # the exact code the finding is about
    confidence: Confidence
    effort: Effort
    fix: Fix | None = None
    references: list[Reference] = []

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_line is not None and self.end_line < self.line:
            raise ValueError("endLine must not be before line")
        return self


class Positive(CamelModel):
    line: int = Field(ge=1)
    comment: str


class AreaScore(CamelModel):
    score: int = Field(ge=1, le=10)
    reason: str = Field(min_length=1)


class ScoreBreakdown(CamelModel):
    correctness: AreaScore
    security: AreaScore
    performance: AreaScore
    readability: AreaScore


class FunctionComplexity(CamelModel):
    name: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    best_case: BigO | None = None
    average_case: BigO | None = None
    worst_case: BigO
    space: BigO
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("endLine must not be before startLine")
        return self


class Complexity(CamelModel):
    time: BigO  # the headline figure: worst case of the code as a whole
    space: BigO
    explanation: str = Field(min_length=1)  # how the figures were worked out
    functions: list[FunctionComplexity]


class AlgorithmAlternative(CamelModel):
    name: str = Field(min_length=1)
    time: BigO
    space: BigO
    tradeoff: str = Field(min_length=1)


class DetectedAlgorithm(CamelModel):
    name: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=1, max_length=40)
    confidence: Confidence
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    evidence: str = Field(min_length=1)  # what in the code shows this algorithm
    summary: str = Field(min_length=1)
    time: BigO
    space: BigO
    assessment: str = Field(min_length=1)  # is it a good choice here?
    alternatives: list[AlgorithmAlternative] = []

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_line < self.start_line:
            raise ValueError("endLine must not be before startLine")
        return self


class Metrics(CamelModel):
    """Facts measured from the code itself, not opinions. None means not measured."""

    total_lines: int = Field(ge=0)
    code_lines: int = Field(ge=0)
    comment_lines: int = Field(ge=0)
    blank_lines: int = Field(ge=0)
    longest_line: int = Field(ge=0)
    function_count: int | None = Field(default=None, ge=0)
    longest_function_lines: int | None = Field(default=None, ge=0)
    max_nesting_depth: int | None = Field(default=None, ge=0)


class ReviewResult(CamelModel):
    purpose: str  # what the code does
    summary: str
    verdict: Verdict
    score: int | None = Field(default=None, ge=1, le=10)  # None only when not assessed
    score_breakdown: ScoreBreakdown | None = None
    priority_fixes: list[str] = Field(max_length=3)  # issue ids, most important first
    issues: list[CodeIssue]
    positives: list[Positive]
    complexity: Complexity | None = None
    algorithms: list[DetectedAlgorithm] = []
    metrics: Metrics
    limitations: list[str] = []

    @model_validator(mode="after")
    def ids_are_consistent(self) -> Self:
        if self.verdict != "not-assessed" and (self.score is None or self.score_breakdown is None):
            raise ValueError("score and scoreBreakdown are required for an assessed review")
        ids = [issue.id for issue in self.issues]
        if len(ids) != len(set(ids)):
            raise ValueError("issue ids must be unique")
        unknown = [i for i in self.priority_fixes if i not in ids]
        if unknown:
            raise ValueError(f"priorityFixes refers to unknown issues: {unknown}")
        return self


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
    reply_style: ReplyStyle = "brief"

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
