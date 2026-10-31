"""Scores the configured model on known snippets. Run it from backend/ with the model server up:

    python -m evals.run_evals                  # all cases
    python -m evals.run_evals -k sql fib       # only cases whose id contains one of these
    python -m evals.run_evals --tag bad-practice          # only cases carrying one of these tags
    python -m evals.run_evals --json out.json  # also save every result, to compare runs

It uses the same settings as the app (REVIEWER is ignored; the model is always used), so choose
the model with LLM_MODEL / LLM_BASE_URL. It needs no database and is not part of the test suite.

What it measures, per case (only the checks listed under "expect" in cases.json):
  found      a finding sits on one of the expected lines (or has the expected category)
  reason     such a finding also mentions what is really wrong (expected keywords), so a
             finding on the right line for the wrong reason does not count
  time       the headline time complexity equals the expected Big-O (spacing, ^, * and · ignored);
             "time_any" accepts any of several equivalent forms
  algorithm  a detected algorithm's name contains the expected name ("algorithm" may be a list:
             any one of them counts); "no_algorithm" lists names that must NOT be claimed
  quiet      no error-severity findings / no more than max_issues findings
  enough     at least min_issues findings (for snippets with several separate problems)
Tags (see "tags" in cases.json) group the summary: basic, complex-algorithm, bad-practice.
Valid-reply rate and time per review are reported too.
"""

import argparse
import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.schemas import ReviewResult
from app.services.llm_reviewer import build_llm_reviewer
from app.services.reviewer import ReviewerError

CASES = Path(__file__).parent / "cases.json"


_SUPERSCRIPTS = str.maketrans("²³", "23")


def norm_o(text: str | None) -> str:
    """Compares Big-O strings loosely: O(n^2), O(n²), O(n * m) and O(nm) all normalise alike."""
    cleaned = (text or "").lower().translate(_SUPERSCRIPTS)
    return re.sub(r"[\s^*·×]", "", cleaned)


def _names(expect_value: str | list[str]) -> list[str]:
    return [expect_value] if isinstance(expect_value, str) else list(expect_value)


def check(result: ReviewResult, expect: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    if "issue_lines" in expect or "issue_category" in expect:
        lines = set(expect.get("issue_lines", []))
        category = expect.get("issue_category")
        checks["found"] = any(
            (not lines or lines & set(range(i.line, (i.end_line or i.line) + 1)))
            and (category is None or i.category == category)
            for i in result.issues
        )
    if "reason_keywords" in expect:
        words = [w.lower() for w in expect["reason_keywords"]]
        lines = set(expect.get("issue_lines", []))
        checks["reason"] = any(
            (not lines or lines & set(range(i.line, (i.end_line or i.line) + 1)))
            and any(w in f"{i.title} {i.explanation} {i.evidence}".lower() for w in words)
            for i in result.issues
        )
    if "time" in expect or "time_any" in expect:
        found = norm_o(result.complexity.time if result.complexity else None)
        wanted = [norm_o(t) for t in [*_names(expect.get("time", [])), *expect.get("time_any", [])]]
        checks["time"] = found in wanted
    if "algorithm" in expect:
        checks["algorithm"] = any(
            name.lower() in a.name.lower()
            for name in _names(expect["algorithm"])
            for a in result.algorithms
        )
    if "no_algorithm" in expect:
        checks["no_false_algorithm"] = not any(
            name.lower() in a.name.lower()
            for name in _names(expect["no_algorithm"])
            for a in result.algorithms
        )
    if "min_issues" in expect:
        checks["enough"] = len(result.issues) >= expect["min_issues"]
    if expect.get("no_errors"):
        checks["quiet"] = not any(i.severity == "error" for i in result.issues)
    if "max_issues" in expect:
        checks["quiet"] = checks.get("quiet", True) and len(result.issues) <= expect["max_issues"]
    return checks


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", nargs="*", help="only cases whose id contains one of these")
    parser.add_argument("--tag", nargs="*", help="only cases carrying one of these tags")
    parser.add_argument("--json", help="write full results to this file")
    args = parser.parse_args()

    settings = get_settings()
    reviewer = build_llm_reviewer(settings)
    status = await reviewer.check()
    print(f"model: {reviewer.model_name}   server: {settings.llm_base_url}   {status['detail']}")
    if not status["ready"]:
        return 2

    cases = [
        c
        for c in json.loads(CASES.read_text())
        if (not args.k or any(k in c["id"] for k in args.k))
        and (not args.tag or set(args.tag) & set(c.get("tags", [])))
    ]
    totals: dict[str, list[bool]] = {}
    by_tag: dict[str, list[bool]] = {}
    valid = 0
    seconds: list[float] = []
    saved: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        try:
            outcome = await reviewer.review(case["code"], case["language"])
        except ReviewerError as exc:
            print(f"{case['id']:<24} FAILED  ({type(exc).__name__}: {exc})")
            saved.append({"id": case["id"], "error": str(exc)})
            continue
        elapsed = time.perf_counter() - started
        valid += 1
        seconds.append(elapsed)
        checks = check(outcome.result, case["expect"])
        for name, ok in checks.items():
            totals.setdefault(name, []).append(ok)
        for tag in case.get("tags", []):
            by_tag.setdefault(tag, []).extend(checks.values())
        marks = "  ".join(f"{n}:{'ok' if ok else 'MISS'}" for n, ok in checks.items())
        print(f"{case['id']:<24} {elapsed:5.1f}s  {marks}")
        saved.append(
            {
                "id": case["id"],
                "seconds": elapsed,
                "checks": checks,
                "result": outcome.result.model_dump(mode="json", by_alias=True),
            }
        )

    print("\nsummary")
    print(f"  valid replies   {valid}/{len(cases)}")
    for name, results in totals.items():
        print(f"  {name:<15} {sum(results)}/{len(results)}")
    if by_tag:
        print("  by tag (all checks)")
        for tag, results in sorted(by_tag.items()):
            print(f"    {tag:<18} {sum(results)}/{len(results)}")
    if seconds:
        print(f"  mean time       {sum(seconds) / len(seconds):.1f}s per review")
    if args.json:
        Path(args.json).write_text(json.dumps(saved, indent=2))  # noqa: ASYNC240
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
