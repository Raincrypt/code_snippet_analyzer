"""Test helpers: a fake model client and a canned model reply."""

import json
from typing import Any

from app.services.llm_client import Completion, LlmError, Message, TextCallback

CODE = """def largest(xs):
    best = xs[0]
    for x in xs:
        if x > best:
            best = x
    return best
"""


def good_reply(**overrides: Any) -> dict[str, Any]:
    reply: dict[str, Any] = {
        "purpose": "Returns the largest value in a list.",
        "summary": "Correct, but crashes on an empty list.",
        "issues": [
            {
                "line": 2,
                "end_line": None,
                "severity": "error",
                "category": "bug",
                "title": "Crashes on empty input",
                "explanation": "xs[0] raises IndexError when xs is empty.",
                "impact": "Callers passing an empty list get an exception.",
                "evidence": "best = xs[0]",
                "confidence": "high",
                "effort": "quick",
                "fix": {
                    "description": "Handle the empty case.",
                    "before": "best = xs[0]",
                    "after": "if not xs:\n    raise ValueError('empty')\nbest = xs[0]",
                },
            }
        ],
        "positives": [{"line": 3, "comment": "Single pass."}],
        "complexity": {
            "time": "O(n)",
            "space": "O(1)",
            "explanation": "One pass over the n items.",
            "functions": [
                {
                    "name": "largest",
                    "start_line": 1,
                    "end_line": 6,
                    "best_case": "O(n)",
                    "average_case": "O(n)",
                    "worst_case": "O(n)",
                    "space": "O(1)",
                    "explanation": "Single loop.",
                }
            ],
        },
        "algorithms": [],
        "area_scores": {
            "correctness": {"score": 9, "reason": "Works for non-empty input."},
            "security": {"score": 10, "reason": "No concerns."},
            "performance": {"score": 9, "reason": "Optimal."},
            "readability": {"score": 8, "reason": "Clear."},
        },
        "limitations": [],
    }
    reply.update(overrides)
    return reply


class FakeClient:
    """Replies with queued texts, in order, and records what it was asked."""

    model = "fake-model"

    def __init__(self, *replies: str | Exception, finish_reason: str = "stop") -> None:
        self.replies = list(replies)
        self.finish_reason = finish_reason
        self.calls: list[list[Message]] = []
        self.schemas: list[dict[str, Any] | None] = []
        self.models = ["fake-model:latest"]

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        on_text: TextCallback | None = None,
    ) -> Completion:
        self.calls.append(messages)
        self.schemas.append(json_schema)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        if on_text is not None:
            for i in range(0, len(reply), 40):  # arrives in small pieces, like a real stream
                await on_text(reply[i : i + 40])
        return Completion(reply, self.finish_reason, tokens_in=100, tokens_out=50)

    async def list_models(self) -> list[str]:
        if not self.models:
            raise LlmError("down")
        return self.models


def as_text(reply: dict[str, Any]) -> str:
    return json.dumps(reply)
