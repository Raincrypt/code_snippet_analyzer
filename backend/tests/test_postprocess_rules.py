"""How the post-processing combines the model's review with the rule-based checks."""

from typing import Any

from app.services.llm_schema import LlmReview
from app.services.postprocess import anchor_evidence, build_result
from tests.llm_fakes import CODE, good_reply


def build(code: str = CODE, language: str = "python", **overrides: Any) -> Any:
    return build_result(LlmReview.model_validate(good_reply(**overrides)), code, language)  # type: ignore[arg-type]


def issue(**fields: Any) -> dict[str, Any]:
    return {**good_reply()["issues"][0], **fields}


def area(correctness: int = 10, security: int = 10, performance: int = 10, readability: int = 10):
    def one(n: int) -> dict[str, Any]:
        return {"score": n, "reason": "because"}

    return {
        "correctness": one(correctness),
        "security": one(security),
        "performance": one(performance),
        "readability": one(readability),
    }


SQL = (
    "def find_user(conn, name):\n    cur = conn.cursor()\n"
    '    cur.execute("SELECT * FROM users WHERE name = \'" + name + "\'")\n'
    "    return cur.fetchall()\n"
)


# ---- rule findings -----------------------------------------------------------------------------


def test_rule_finding_appears_even_when_the_model_found_nothing() -> None:
    result = build(SQL, issues=[], area_scores=area(security=2))
    assert [(i.line, i.category, i.severity) for i in result.issues] == [(3, "security", "error")]
    assert result.issues[0].fix is not None
    assert result.verdict == "fix-before-use"
    assert any("rule-based" in text for text in result.limitations)


def test_rule_replaces_the_model_s_version_of_the_same_problem() -> None:
    model_version = issue(
        line=3,
        severity="warning",
        category="security",
        title="SQL injection possible",
        evidence='cur.execute("SELECT * FROM users WHERE name = \'" + name + "\'")',
    )
    result = build(SQL, issues=[model_version], area_scores=area(security=3))
    assert len(result.issues) == 1 and result.issues[0].severity == "error"


def test_unrelated_model_finding_is_kept_alongside_a_rule_finding() -> None:
    other = issue(
        line=2,
        severity="info",
        category="style",
        title="Name it better",
        evidence="cur = conn.cursor()",
    )
    result = build(SQL, issues=[other], area_scores=area(security=3))
    assert len(result.issues) == 2


def test_syntax_error_becomes_a_finding() -> None:
    result = build("def f(:\n    pass\n", issues=[], complexity=None)
    assert result.issues[0].title.startswith("Syntax error")
    assert result.issues[0].line == 1 and result.verdict == "fix-before-use"


def test_non_python_gets_no_rules_and_says_so() -> None:
    result = build(SQL, "javascript", issues=[])
    assert result.issues == []
    assert any("Python only" in text for text in result.limitations)


# ---- evidence ----------------------------------------------------------------------------------


def test_misquoted_evidence_is_repaired_not_dropped() -> None:
    wrong = issue(line=3, evidence="cur.execute('SELECT * FROM users WHERE name = ' + name)")
    result = build(SQL, issues=[wrong], area_scores=area(correctness=5))
    assert len(result.issues) >= 1
    assert any(
        "quoted the code slightly wrongly" in t or "rule-based" in t for t in result.limitations
    )


def test_anchor_accepts_close_quotes_and_rejects_unrelated_code() -> None:
    lines = SQL.splitlines()
    assert anchor_evidence(
        "cur.execute('SELECT * FROM users WHERE name = ' + name)", lines, 3, None
    )
    assert anchor_evidence("os.system(command)", lines, 3, None) is None


# ---- things the code disproves -----------------------------------------------------------------


def test_missing_docstring_remark_is_dropped_when_there_is_a_docstring() -> None:
    code = 'def add(a, b):\n    """Add two numbers."""\n    return a + b\n'
    remark = issue(
        line=1,
        category="style",
        severity="warning",
        title="Missing docstring",
        explanation="The function has no docstring.",
        evidence="def add(a, b):",
    )
    assert build(code, issues=[remark]).issues == []


def test_invented_function_names_are_dropped_from_the_table() -> None:
    complexity = good_reply()["complexity"]
    complexity["functions"][0]["name"] = "largest_value"  # not in the code
    result = build(complexity=complexity)
    assert result.complexity is not None and result.complexity.functions == []
    assert any("no function with that name" in t for t in result.limitations)


def test_function_line_range_comes_from_the_code() -> None:
    complexity = good_reply()["complexity"]
    complexity["functions"][0].update(start_line=2, end_line=3)
    result = build(complexity=complexity)
    assert result.complexity is not None
    fn = result.complexity.functions[0]
    assert (fn.start_line, fn.end_line) == (1, 6)


def test_style_remarks_never_count_as_warnings() -> None:
    nit = issue(category="style", severity="warning", confidence="high", title="Nit")
    result = build(issues=[nit])
    assert result.issues[0].severity == "info"


# ---- complexity and algorithms -----------------------------------------------------------------


def test_missing_complexity_is_filled_in_for_trivial_code() -> None:
    code = "def add(a, b):\n    return a + b\n"
    result = build(code, issues=[], complexity=None)
    assert result.complexity is not None
    assert (result.complexity.time, result.complexity.space) == ("O(1)", "O(1)")
    assert any("not by the model" in t for t in result.limitations)


def test_missing_complexity_is_not_guessed_for_anything_else() -> None:
    assert build(issues=[], complexity=None).complexity is None


def test_recognised_algorithm_uses_catalogue_figures() -> None:
    binary = (
        "def s(xs, t):\n    lo, hi = 0, len(xs) - 1\n    while lo <= hi:\n"
        "        mid = (lo + hi) // 2\n        if xs[mid] == t:\n            return mid\n"
        "        if xs[mid] < t:\n            lo = mid + 1\n        else:\n"
        "            hi = mid - 1\n    return -1\n"
    )
    result = build(binary, issues=[], algorithms=[], complexity=None)
    assert [(a.name, a.time, a.space, a.confidence) for a in result.algorithms] == [
        ("Binary search", "O(log n)", "O(1)", "high")
    ]
    assert result.algorithms[0].alternatives
    assert result.metrics.function_count == 1


def test_unconfirmed_standard_algorithm_is_low_confidence_in_python() -> None:
    claim = {
        "name": "binary search", "category": "search", "confidence": "high",
        "start_line": 1, "end_line": 6, "evidence": "for x in xs:", "summary": "s",
        "time": "O(n)", "space": "O(1)", "assessment": "a", "alternatives": [],
    }  # fmt: skip
    # CODE is a linear scan, so the structural check does not confirm binary search.
    result = build(algorithms=[claim])
    assert [(a.confidence, a.time) for a in result.algorithms] == [("low", "O(n)")]


def test_standard_algorithm_in_another_language_gets_standard_figures() -> None:
    claim = {
        "name": "Binary search", "category": "search", "confidence": "high",
        "start_line": 1, "end_line": 6, "evidence": "for x in xs:", "summary": "s",
        "time": "O(n)", "space": "O(n)", "assessment": "a", "alternatives": [],
    }  # fmt: skip
    result = build(language="javascript", algorithms=[claim])
    assert [(a.confidence, a.time, a.space) for a in result.algorithms] == [
        ("high", "O(log n)", "O(1)")
    ]


def test_plain_recursion_is_not_dynamic_programming() -> None:
    fib = "def fib(n):\n    if n < 2:\n        return n\n    return fib(n - 1) + fib(n - 2)\n"
    claim = {
        "name": "Fibonacci sequence", "category": "Dynamic Programming", "confidence": "high",
        "start_line": 1, "end_line": 4, "evidence": "return fib(n - 1) + fib(n - 2)",
        "summary": "s", "time": "O(2^n)", "space": "O(n)", "assessment": "a", "alternatives": [],
    }  # fmt: skip
    result = build(fib, issues=[], algorithms=[claim], complexity=None)
    assert result.algorithms == []
    assert any("algorithm claim" in t for t in result.limitations)
    assert [(i.category, i.line) for i in result.issues] == [("performance", 4)]


# ---- score and verdict -------------------------------------------------------------------------


def test_an_error_caps_the_score_even_when_the_areas_look_fine() -> None:
    result = build(area_scores=area(correctness=10))
    assert result.score is not None and result.score <= 5
    assert result.verdict == "fix-before-use"


def test_a_security_error_caps_lower() -> None:
    result = build(SQL, issues=[], area_scores=area(security=9))
    assert result.score is not None and result.score <= 4


def test_weakest_area_limits_the_score() -> None:
    result = build(issues=[], area_scores=area(performance=2))
    assert result.score is not None and result.score <= 5
    assert result.verdict == "needs-work"


def test_low_area_score_without_a_finding_is_flagged_as_unsupported() -> None:
    result = build(issues=[], area_scores=area(performance=3))
    assert any("performance 3/10" in t and "no specific finding" in t for t in result.limitations)


def test_clean_code_keeps_a_high_score() -> None:
    result = build(issues=[], area_scores=area())
    assert result.score == 10 and result.verdict == "looks-good"


def test_warnings_cap_the_score_at_eight() -> None:
    warning = issue(severity="warning", category="performance", title="Slow loop", line=3,
                    evidence="for x in xs:")  # fmt: skip
    result = build(issues=[warning], area_scores=area())
    assert result.score is not None and result.score <= 8


def test_positives_are_limited_to_two() -> None:
    many = [{"line": n, "comment": f"good {n}"} for n in range(1, 6)]
    assert len(build(positives=many).positives) == 2
