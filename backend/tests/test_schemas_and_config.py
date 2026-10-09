import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import CodeIssue, FunctionComplexity, ReviewResult


def issue(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "f1",
        "line": 3,
        "severity": "error",
        "category": "bug",
        "title": "T",
        "explanation": "E",
        "impact": "I",
        "evidence": "x",
        "confidence": "high",
        "effort": "quick",
    }
    return base | overrides


def test_issue_accepts_camel_case_input() -> None:
    parsed = CodeIssue.model_validate(issue(endLine=5))
    assert parsed.end_line == 5


def test_issue_end_line_cannot_precede_line() -> None:
    with pytest.raises(ValidationError):
        CodeIssue.model_validate(issue(line=5, endLine=2))


def test_issue_line_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        CodeIssue.model_validate(issue(line=0))


def not_assessed(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "purpose": "p",
        "summary": "s",
        "verdict": "not-assessed",
        "priorityFixes": [],
        "issues": [],
        "positives": [],
        "metrics": {
            "totalLines": 1,
            "codeLines": 1,
            "commentLines": 0,
            "blankLines": 0,
            "longestLine": 1,
        },
    }
    return base | overrides


@pytest.mark.parametrize("score", [0, 11])
def test_score_must_be_between_1_and_10(score: int) -> None:
    with pytest.raises(ValidationError):
        ReviewResult.model_validate(not_assessed(score=score))


def test_an_assessed_review_needs_a_score_and_breakdown() -> None:
    with pytest.raises(ValidationError, match="required for an assessed review"):
        ReviewResult.model_validate(not_assessed(verdict="needs-work"))


def test_issue_ids_must_be_unique() -> None:
    with pytest.raises(ValidationError, match="unique"):
        ReviewResult.model_validate(not_assessed(issues=[issue(), issue()]))


def test_priority_fixes_must_refer_to_real_issues() -> None:
    with pytest.raises(ValidationError, match="unknown issues"):
        ReviewResult.model_validate(not_assessed(priorityFixes=["nope"]))


def test_at_most_three_priority_fixes() -> None:
    with pytest.raises(ValidationError):
        ReviewResult.model_validate(not_assessed(priorityFixes=["a", "b", "c", "d"]))


@pytest.mark.parametrize("value", ["O(n)", "O(n log n)", "O(n²)", "O(2^n)", "O(V + E)", "O(1)"])
def test_big_o_accepts_common_notation(value: str) -> None:
    FunctionComplexity.model_validate(
        {
            "name": "f",
            "startLine": 1,
            "endLine": 2,
            "worstCase": value,
            "space": "O(1)",
            "explanation": "x",
        }
    )


@pytest.mark.parametrize("value", ["n squared", "fast", "O()", "O(n", ""])
def test_big_o_rejects_other_text(value: str) -> None:
    with pytest.raises(ValidationError):
        FunctionComplexity.model_validate(
            {
                "name": "f",
                "startLine": 1,
                "endLine": 2,
                "worstCase": value,
                "space": "O(1)",
                "explanation": "x",
            }
        )


def test_function_and_algorithm_ranges_must_not_run_backwards() -> None:
    with pytest.raises(ValidationError):
        FunctionComplexity.model_validate(
            {
                "name": "f",
                "startLine": 5,
                "endLine": 2,
                "worstCase": "O(1)",
                "space": "O(1)",
                "explanation": "x",
            }
        )


def test_postgres_urls_get_the_async_driver() -> None:
    assert (
        Settings(database_url="postgres://u:p@h/db").database_url == "postgresql+asyncpg://u:p@h/db"
    )
    assert (
        Settings(database_url="postgresql://u:p@h/db").database_url
        == "postgresql+asyncpg://u:p@h/db"
    )


def test_sqlite_urls_are_left_alone() -> None:
    url = "sqlite+aiosqlite:///./x.db"
    assert Settings(database_url=url).database_url == url


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com ,")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_docs_are_off_in_production() -> None:
    assert Settings(environment="production").docs_enabled is False
