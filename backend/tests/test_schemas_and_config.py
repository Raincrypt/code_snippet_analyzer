import pytest
from pydantic import ValidationError

from app.config import Settings
from app.schemas import CodeIssue, ReviewResult


def issue(**overrides: object) -> dict[str, object]:
    base = {"line": 3, "severity": "error", "category": "bug", "title": "T", "description": "D"}
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


@pytest.mark.parametrize("score", [0, 11])
def test_score_must_be_between_1_and_10(score: int) -> None:
    with pytest.raises(ValidationError):
        ReviewResult.model_validate({"summary": "s", "score": score, "issues": [], "positives": []})


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
