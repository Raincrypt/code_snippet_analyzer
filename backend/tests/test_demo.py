"""The example review is shared with the frontend, so it must be valid and honest."""

import json

from app.schemas import ReviewResult
from app.services.demo import DEMO_DIR, demo_review_for, load_demo
from app.services.metrics import measure


def test_the_demo_files_exist_and_validate() -> None:
    demo = load_demo()
    assert demo is not None, f"expected demo files in {DEMO_DIR}"
    assert isinstance(demo.review, ReviewResult)


def test_every_finding_quotes_the_code_that_starts_on_its_cited_line() -> None:
    """The same grounding rule the real reviewer's output will have to pass."""
    demo = load_demo()
    assert demo is not None
    lines = demo.code.split("\n")
    for issue in demo.review.issues:
        for offset, quoted in enumerate(issue.evidence.split("\n")):
            actual = lines[issue.line - 1 + offset]
            assert " ".join(quoted.split()) == " ".join(actual.split()), (
                f"{issue.id}: line {issue.line + offset} does not match its quoted evidence"
            )


def test_algorithm_and_function_ranges_fit_inside_the_code() -> None:
    demo = load_demo()
    assert demo is not None and demo.review.complexity is not None
    total = len(demo.code.split("\n"))
    ranges = [(a.start_line, a.end_line) for a in demo.review.algorithms]
    ranges += [(f.start_line, f.end_line) for f in demo.review.complexity.functions]
    assert all(1 <= start <= end <= total for start, end in ranges)


def test_measured_numbers_match_the_actual_code() -> None:
    demo = load_demo()
    assert demo is not None
    measured = measure(demo.code)
    shown = demo.review.metrics
    assert (shown.total_lines, shown.code_lines, shown.comment_lines, shown.blank_lines) == (
        measured.total_lines,
        measured.code_lines,
        measured.comment_lines,
        measured.blank_lines,
    )
    assert shown.longest_line == measured.longest_line


def test_the_review_json_uses_the_wire_format() -> None:
    raw = json.loads((DEMO_DIR / "review.json").read_text(encoding="utf-8"))
    assert "scoreBreakdown" in raw and "priorityFixes" in raw


def test_only_the_exact_sample_gets_the_example() -> None:
    demo = load_demo()
    assert demo is not None
    assert demo_review_for(demo.code + "\n") is not None  # trailing whitespace is ignored
    assert demo_review_for(demo.code + "\nconsole.log(1)") is None
