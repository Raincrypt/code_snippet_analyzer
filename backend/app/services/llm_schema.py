"""What the model is asked to produce.

This is deliberately simpler than `ReviewResult`: no ids, no score, no metrics, and no pattern or
length rules (constrained decoding handles loose types more reliably). Everything the program can
work out for itself (ids, priority order, score, verdict, metrics) is computed afterwards in
`postprocess.py`, and the result is checked against the strict `ReviewResult`.

The field order matters: the model writes them in this order, and the reviewer uses it to report
progress (issues come before complexity).
"""

from pydantic import BaseModel, ConfigDict

from app.schemas import Category, Confidence, Effort, Severity


class LlmModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LlmFix(LlmModel):
    description: str
    before: str | None = None
    after: str


class LlmIssue(LlmModel):
    line: int
    end_line: int | None = None
    severity: Severity
    category: Category
    title: str
    explanation: str
    impact: str
    evidence: str
    confidence: Confidence
    effort: Effort
    fix: LlmFix | None = None


class LlmPositive(LlmModel):
    line: int
    comment: str


class LlmFunction(LlmModel):
    name: str
    start_line: int
    end_line: int
    best_case: str | None = None
    average_case: str | None = None
    worst_case: str
    space: str
    explanation: str


class LlmComplexity(LlmModel):
    time: str
    space: str
    explanation: str
    functions: list[LlmFunction] = []


class LlmAlternative(LlmModel):
    name: str
    time: str
    space: str
    tradeoff: str


class LlmAlgorithm(LlmModel):
    name: str
    category: str
    confidence: Confidence
    start_line: int
    end_line: int
    evidence: str
    summary: str
    time: str
    space: str
    assessment: str
    alternatives: list[LlmAlternative] = []


class LlmArea(LlmModel):
    score: int
    reason: str


class LlmAreaScores(LlmModel):
    correctness: LlmArea
    security: LlmArea
    performance: LlmArea
    readability: LlmArea


class LlmReview(LlmModel):
    purpose: str
    summary: str
    issues: list[LlmIssue] = []
    positives: list[LlmPositive] = []
    complexity: LlmComplexity | None = None
    algorithms: list[LlmAlgorithm] = []
    area_scores: LlmAreaScores
    limitations: list[str] = []
