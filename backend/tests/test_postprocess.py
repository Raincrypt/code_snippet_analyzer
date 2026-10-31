from typing import Any

from app.services.llm_schema import LlmReview
from app.services.postprocess import (
    build_result,
    clean_big_o,
    clean_evidence,
    locate_evidence,
    overall_score,
    verdict_for,
)
from tests.llm_fakes import CODE, good_reply

LINES = CODE.splitlines()


def build(**overrides: Any) -> Any:
    return build_result(LlmReview.model_validate(good_reply(**overrides)), CODE)


def issue(**fields: Any) -> dict[str, Any]:
    base = good_reply()["issues"][0]
    return {**base, **fields}


def test_clean_big_o() -> None:
    assert clean_big_o("O(n^2)") == "O(n^2)"
    assert clean_big_o("O(n  log  n)") == "O(n log n)"
    assert clean_big_o("O(n) in the worst case") == "O(n)"
    assert clean_big_o("Θ(n log n)") == "O(n log n)"
    assert clean_big_o("O(log(n))") == "O(log(n))"
    assert clean_big_o("linear") is None
    assert clean_big_o(None) is None


def test_clean_evidence_strips_line_prefix() -> None:
    assert clean_evidence("  2 |     best = xs[0]") == "best = xs[0]"
    assert clean_evidence("2 | a\n3 | b") == "a\nb"


def test_evidence_found_where_claimed() -> None:
    assert locate_evidence("best = xs[0]", LINES, 2, None) == (2, None)


def test_evidence_ignores_indentation() -> None:
    assert locate_evidence("if x   >  best:", LINES, 4, None) == (4, None)


def test_evidence_moved_to_real_line() -> None:
    assert locate_evidence("best = xs[0]", LINES, 5, None) == (2, None)


def test_multiline_evidence_gets_end_line() -> None:
    assert locate_evidence("for x in xs:\n    if x > best:", LINES, 9, None) == (3, 4)


def test_evidence_missing_is_none() -> None:
    assert locate_evidence("return None", LINES, 2, None) is None
    assert locate_evidence("ab", LINES, 2, None) is None  # too short to mean anything


def test_good_review_is_converted() -> None:
    result = build()
    assert [i.id for i in result.issues] == ["I1"]
    assert result.issues[0].line == 2
    assert result.priority_fixes == ["I1"]
    assert result.complexity is not None and result.complexity.time == "O(n)"
    assert result.metrics.total_lines == 6  # measured from the code, not by the model
    assert result.verdict == "fix-before-use"


def test_invented_finding_is_dropped_and_reported() -> None:
    result = build(issues=[issue(), issue(evidence="os.system(cmd)", title="Shell injection")])
    assert len(result.issues) == 1
    assert any("removed" in text for text in result.limitations)


def test_wrong_line_is_corrected_and_reported() -> None:
    result = build(issues=[issue(line=5)])
    assert result.issues[0].line == 2
    assert any("corrected" in text for text in result.limitations)


def test_line_outside_code_is_dropped() -> None:
    assert build(issues=[issue(line=99)]).issues == []


def test_duplicates_are_merged() -> None:
    assert len(build(issues=[issue(), issue()]).issues) == 1


def test_low_confidence_error_becomes_warning() -> None:
    result = build(issues=[issue(confidence="low")])
    assert result.issues[0].severity == "warning"
    assert result.verdict != "fix-before-use"


def test_issues_sorted_by_severity_and_get_sequential_ids() -> None:
    warning = issue(
        severity="warning", title="Slow", line=3, evidence="for x in xs:", category="performance"
    )
    result = build(issues=[warning, issue()])
    assert [(i.id, i.severity) for i in result.issues] == [("I1", "error"), ("I2", "warning")]
    assert result.priority_fixes == ["I1", "I2"]


def test_issue_cap() -> None:
    # Different lines and categories, so none of them counts as a repeat of another.
    many = [
        issue(
            line=n, evidence=LINES[n - 1].strip(), title=f"Problem {n}", severity="info", category=c
        )
        for n in range(1, 7)
        for c in ("bug", "security", "performance")
    ]
    assert len(build(issues=many).issues) == 15


def test_bad_complexity_is_discarded_with_note() -> None:
    bad = {**good_reply()["complexity"], "time": "fast"}
    result = build(complexity=bad)
    assert result.complexity is None
    assert any("complexity" in text.lower() for text in result.limitations)


def test_bad_function_entry_is_dropped_but_rest_kept() -> None:
    complexity = good_reply()["complexity"]
    complexity["functions"].append(
        {**complexity["functions"][0], "name": "x", "worst_case": "slow"}
    )
    result = build(complexity=complexity)
    assert result.complexity is not None
    assert [f.name for f in result.complexity.functions] == ["largest"]


def test_guessed_algorithm_is_dropped() -> None:
    algorithm = {
        "name": "Binary search",
        "category": "search",
        "confidence": "high",
        "start_line": 1,
        "end_line": 6,
        "evidence": "mid = (lo + hi) // 2",
        "summary": "Halves the range.",
        "time": "O(log n)",
        "space": "O(1)",
        "assessment": "Good.",
        "alternatives": [],
    }
    assert build(algorithms=[algorithm]).algorithms == []
    real = {**algorithm, "name": "Linear scan", "evidence": "for x in xs:", "time": "O(n)"}
    assert [a.name for a in build(algorithms=[real]).algorithms] == ["Linear scan"]


def test_area_score_is_capped_by_findings() -> None:
    result = build()  # model said correctness 9, but one confident error was found
    assert result.score_breakdown is not None
    assert result.score_breakdown.correctness.score == 6
    assert result.score_breakdown.security.score == 10


def test_clean_code_scores_from_model() -> None:
    result = build(issues=[])
    assert result.score == 9
    assert result.verdict == "looks-good"


def test_verdict_rules() -> None:
    assert verdict_for(10, []) == "looks-good"
    assert verdict_for(8, []) == "mostly-fine"
    assert verdict_for(4, []) == "needs-work"
    warnings = build(issues=[issue(severity="warning")]).issues
    assert verdict_for(9, warnings) == "mostly-fine"
    assert verdict_for(9, warnings * 2) == "needs-work"


def test_overall_score_is_weighted() -> None:
    result = build(issues=[])
    assert result.score_breakdown is not None
    assert overall_score(result.score_breakdown, result.issues) == result.score


def test_missing_optional_parts_are_fine() -> None:
    result = build(complexity=None, issues=[], positives=[], algorithms=[])
    assert result.complexity is None and result.issues == []
