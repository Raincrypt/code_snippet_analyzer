"""The rule-based checks alone (no AI model) must handle the eval snippets that carry a "rules"
expectation. This keeps the deterministic part of the review honest and runs in CI."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.llm_schema import LlmReview
from app.services.postprocess import build_result
from evals.run_evals import check

CASES = [
    c
    for c in json.loads((Path(__file__).parents[1] / "evals" / "cases.json").read_text())
    if "rules" in c
]

# What a model that found nothing at all would return.
SILENT_MODEL = LlmReview.model_validate(
    {
        "purpose": "x",
        "summary": "x",
        "area_scores": {
            area: {"score": 10, "reason": "x"}
            for area in ("correctness", "security", "performance", "readability")
        },
    }
)


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_rules_alone(case: dict[str, Any]) -> None:
    result = build_result(SILENT_MODEL, case["code"], case["language"])
    checks = check(result, case["rules"])
    assert checks, "the case checks nothing"
    assert all(checks.values()), f"{case['id']}: {checks}"
