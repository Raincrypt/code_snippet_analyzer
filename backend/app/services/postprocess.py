"""Turns the model's raw review into a trustworthy `ReviewResult`, using plain code, not AI.

A model is good at reading code and bad at counting, citing and arithmetic. So everything that
can be checked or computed is done here:

- line numbers are checked against the real code, and each finding's quoted evidence must really
  appear there (a finding is moved to where its evidence is, or dropped if it is nowhere);
- for Python, rule-based checks (`static_python.py`) add the findings and algorithms a model tends
  to miss, and their facts win over the model's;
- ids, priority order, score and verdict come from fixed rules, not from the model;
- Big-O strings are cleaned up, and measurements come from the code itself.

Every correction is counted and reported in `limitations`, so the reader knows it happened.
"""

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.schemas import (
    AlgorithmAlternative,
    AreaScore,
    Category,
    CodeIssue,
    Complexity,
    Confidence,
    DetectedAlgorithm,
    Effort,
    Fix,
    FunctionComplexity,
    Language,
    Positive,
    ReviewResult,
    ScoreBreakdown,
    Severity,
    Verdict,
)
from app.services.algorithm_catalog import CATALOG, CatalogEntry, find_entry
from app.services.llm_schema import LlmArea, LlmIssue, LlmReview
from app.services.metrics import measure
from app.services.static_python import StaticAnalysis, analyse

MAX_ISSUES = 15
MAX_POSITIVES = 2
SEVERITY_ORDER: dict[Severity, int] = {"error": 0, "warning": 1, "info": 2, "suggestion": 3}
CONFIDENCE_ORDER: dict[Confidence, int] = {"high": 0, "medium": 1, "low": 2}
# How much each area counts towards the overall score.
AREA_WEIGHTS = {"correctness": 0.35, "security": 0.25, "performance": 0.20, "readability": 0.20}
AREA_OF_CATEGORY = {
    "bug": "correctness",
    "security": "security",
    "performance": "performance",
    "style": "readability",
    "best-practice": "readability",
}

_LINE_PREFIX = re.compile(r"^\s*\d+\s*\|\s?", re.MULTILINE)
_BIG_O = re.compile(r"[OΘ]\((?:[^()]|\([^()]*\))+\)")


@dataclass
class Corrections:
    """What was fixed or dropped, so it can be reported honestly."""

    dropped_issues: int = 0
    moved_issues: int = 0
    repaired_evidence: int = 0
    dropped_algorithms: int = 0
    dropped_names: int = 0
    rule_findings: int = 0
    downgraded_issues: int = 0
    dropped_other: int = 0
    notes: list[str] = field(default_factory=list)


def squash(text: str) -> str:
    """Collapses all whitespace, so indentation differences do not matter when matching."""
    return " ".join(text.split())


def clean_evidence(text: str) -> str:
    """Models sometimes copy the `NN |` prefix into the quoted code; remove it."""
    return _LINE_PREFIX.sub("", text).strip()


def clean_big_o(value: str | None) -> str | None:
    """'O(n^2) in the worst case' -> 'O(n^2)'; anything that is not Big-O -> None."""
    if value is None:
        return None
    match = _BIG_O.search(value.replace("Θ", "O").strip())
    if match is None:
        return None
    result = squash(match.group(0))
    return result if len(result) <= 40 else None


def clamp_lines(start: int, end: int | None, total: int) -> tuple[int, int | None] | None:
    """Keeps line numbers inside the code; None if the start is outside it."""
    if start < 1 or start > total:
        return None
    if end is None or end <= start:
        return start, None
    return start, min(end, total)


def locate_evidence(
    evidence: str, lines: list[str], line: int, end_line: int | None
) -> tuple[int, int | None] | None:
    """Finds where the quoted code really is, preferring the position the model claimed.

    Returns the (possibly corrected) line range, or None if the evidence is not in the code.
    """
    wanted = squash(clean_evidence(evidence))
    if len(wanted) < 3:
        return None
    count = max(1, len(clean_evidence(evidence).splitlines()))
    total = len(lines)

    # 1. Is it where the model said (with a little slack)?
    lo = max(0, line - 3)
    hi = min(total, max(end_line or line, line + count - 1) + 2)
    if wanted in squash("\n".join(lines[lo:hi])):
        return line, end_line

    # 2. Otherwise find the closest line holding the first line of the evidence.
    first = squash(clean_evidence(evidence).splitlines()[0])
    if len(first) < 3:
        return None
    candidates = [i for i, text in enumerate(lines) if first in squash(text)]
    for index in sorted(candidates, key=lambda i: abs(i + 1 - line)):
        window = squash("\n".join(lines[index : index + count + 1]))
        if wanted in window:
            start = index + 1
            return start, (min(start + count - 1, total) if count > 1 else None)
    return None


FUZZY_MIN = 0.55  # how alike (0 to 1) a quote must be to the real code to be accepted


def anchor_evidence(
    evidence: str, lines: list[str], line: int, end_line: int | None
) -> tuple[int, int | None, bool] | None:
    """Where a finding really is: (start, end, exact), or None if nothing like it is nearby.

    Small models often misquote code slightly (changed quotes, dropped brackets). An exact match
    is best; failing that, the closest-looking lines near the claimed position are accepted. The
    program then shows the real code instead of the model's quote.
    """
    exact = locate_evidence(evidence, lines, line, end_line)
    if exact is not None:
        return exact[0], exact[1], True

    quoted = clean_evidence(evidence)
    wanted = squash(quoted)
    if len(wanted) < 3:
        return None
    count = max(1, min(len(quoted.splitlines()), 8))
    best_ratio, best_index = 0.0, -1
    for index in range(max(0, line - 4), min(len(lines), (end_line or line) + 3)):
        chunk = squash("\n".join(lines[index : index + count]))
        if not chunk:
            continue
        ratio = SequenceMatcher(None, wanted, chunk).ratio()
        if ratio > best_ratio:
            best_ratio, best_index = ratio, index
    if best_index < 0 or best_ratio < FUZZY_MIN:
        return None
    start = best_index + 1
    return start, (min(start + count - 1, len(lines)) if count > 1 else None), False


def code_at(lines: list[str], start: int, end: int | None, limit: int = 8) -> str:
    """The real code on those lines, trimmed to a sensible length."""
    chunk = lines[start - 1 : (end or start)][:limit]
    return "\n".join(chunk).rstrip()[:800]


def severity_for(issue: LlmIssue) -> Severity:
    """Keeps severity honest.

    An error needs at least medium confidence, otherwise it is a warning. A style remark is never
    more than information: it cannot make code "need work".
    """
    if issue.category == "style" and issue.severity in ("error", "warning"):
        return "info"
    if issue.severity == "error" and issue.confidence == "low":
        return "warning"
    return issue.severity


@dataclass
class Candidate:
    """A finding on its way to becoming a `CodeIssue` (before sorting and numbering)."""

    line: int
    end_line: int | None
    severity: Severity
    category: Category
    title: str
    explanation: str
    impact: str
    evidence: str
    confidence: Confidence
    effort: Effort
    fix: Fix | None
    from_rule: bool = False


def contradicted(issue: LlmIssue, line: int, analysis: StaticAnalysis | None) -> bool:
    """A remark the code itself disproves, e.g. "missing docstring" on a documented function."""
    if analysis is None or not analysis.parsed:
        return False
    if "docstring" not in f"{issue.title} {issue.explanation}".lower():
        return False
    owner = [f for f in analysis.functions if f.start_line <= line <= f.end_line]
    return bool(owner) and owner[-1].has_docstring


def model_candidates(
    raw: list[LlmIssue],
    lines: list[str],
    fixes: Corrections,
    analysis: StaticAnalysis | None = None,
) -> list[Candidate]:
    total = len(lines)
    seen: set[tuple[int, str]] = set()
    kept: list[Candidate] = []
    for issue in raw:
        title = squash(issue.title)[:120]
        texts = (title, issue.explanation.strip(), issue.impact.strip(), issue.evidence.strip())
        span = clamp_lines(issue.line, issue.end_line, total)
        if not all(texts) or span is None:
            fixes.dropped_issues += 1
            continue
        located = anchor_evidence(issue.evidence, lines, *span)
        if located is None:
            fixes.dropped_issues += 1
            continue
        start, end, exact = located
        if issue.category == "style" and issue.confidence == "low":
            continue  # unsure style remarks are noise
        if contradicted(issue, start, analysis):
            fixes.dropped_issues += 1
            continue
        if not exact:
            fixes.repaired_evidence += 1
        elif (start, end) != span:
            fixes.moved_issues += 1
        key = (start, issue.category)
        if key in seen:
            continue  # the same kind of finding on the same line twice
        seen.add(key)
        severity = severity_for(issue)
        if severity != issue.severity:
            fixes.downgraded_issues += 1
        fix = None
        if issue.fix and issue.fix.after.strip() and issue.fix.description.strip():
            fix = Fix(
                description=issue.fix.description.strip(),
                before=issue.fix.before or None,
                after=issue.fix.after,
            )
        kept.append(
            Candidate(
                line=start,
                end_line=end,
                severity=severity,
                category=issue.category,
                title=title,
                explanation=issue.explanation.strip(),
                impact=issue.impact.strip(),
                evidence=clean_evidence(issue.evidence) if exact else code_at(lines, start, end),
                confidence=issue.confidence,
                effort=issue.effort,
                fix=fix,
            )
        )
    return kept


def rule_candidates(analysis: StaticAnalysis, lines: list[str]) -> list[Candidate]:
    """Findings from the rule-based checks, in the same shape as the model's."""
    out: list[Candidate] = []
    if analysis.syntax_error is not None:
        number, message = analysis.syntax_error
        number = min(max(number, 1), max(len(lines), 1))
        out.append(
            Candidate(
                line=number,
                end_line=None,
                severity="error",
                category="bug",
                title=f"Syntax error: {message}"[:120],
                explanation=(
                    f"Python cannot read this code: {message}. Nothing after this point can run, "
                    "and the rest of the review may be less reliable."
                ),
                impact="The program fails to start or import.",
                evidence=code_at(lines, number, None) or "(empty line)",
                confidence="high",
                effort="quick",
                fix=None,
                from_rule=True,
            )
        )
    for f in analysis.findings:
        end = f.end_line if f.end_line and f.end_line > f.line else None
        out.append(
            Candidate(
                line=f.line,
                end_line=end,
                severity=f.severity,
                category=f.category,
                title=f.title[:120],
                explanation=f.explanation,
                impact=f.impact,
                evidence=code_at(lines, f.line, end) or "(empty line)",
                confidence=f.confidence,
                effort=f.effort,
                fix=(
                    Fix(description=f.fix_description, before=None, after=f.fix_after)
                    if f.fix_description and f.fix_after
                    else None
                ),
                from_rule=True,
            )
        )
    return out


_WORDS = re.compile(r"[a-z]{5,}")


def same_problem(model: Candidate, rule: Candidate) -> bool:
    """Is a model finding the same problem a rule already reported?"""
    near = (
        model.line <= (rule.end_line or rule.line) + 1
        and rule.line <= (model.end_line or model.line) + 1
    )
    if not near:
        return False
    if AREA_OF_CATEGORY[model.category] == AREA_OF_CATEGORY[rule.category]:
        return True
    return bool(set(_WORDS.findall(model.title.lower())) & set(_WORDS.findall(rule.title.lower())))


def convert_issues(
    raw: list[LlmIssue],
    lines: list[str],
    fixes: Corrections,
    analysis: StaticAnalysis | None = None,
) -> list[CodeIssue]:
    model = model_candidates(raw, lines, fixes, analysis)
    rules = rule_candidates(analysis, lines) if analysis is not None else []
    # A rule is exact where the model is not, so when both report the same problem, keep the rule.
    kept = rules + [m for m in model if not any(same_problem(m, r) for r in rules)]
    fixes.rule_findings = len(rules)

    kept.sort(key=lambda c: (SEVERITY_ORDER[c.severity], CONFIDENCE_ORDER[c.confidence], c.line))
    if len(kept) > MAX_ISSUES:
        fixes.dropped_other += len(kept) - MAX_ISSUES
        kept = kept[:MAX_ISSUES]
    return [
        CodeIssue(
            id=f"I{number}",
            line=c.line,
            end_line=c.end_line,
            severity=c.severity,
            category=c.category,
            title=c.title,
            explanation=c.explanation,
            impact=c.impact,
            evidence=c.evidence,
            confidence=c.confidence,
            effort=c.effort,
            fix=c.fix,
        )
        for number, c in enumerate(kept, start=1)
    ]


def name_in_code(name: str, code: str) -> bool:
    """Does this function name really appear in the code (as a whole word)?"""
    last = name.strip().split(".")[-1]
    return bool(last) and re.search(rf"(?<!\w){re.escape(last)}(?!\w)", code) is not None


def convert_complexity(
    raw: LlmReview, code: str, analysis: StaticAnalysis, fixes: Corrections
) -> Complexity | None:
    total = len(code.splitlines())
    c = raw.complexity
    if c is None:
        return trivial_complexity(analysis, fixes)
    time, space = clean_big_o(c.time), clean_big_o(c.space)
    if time is None or space is None or not c.explanation.strip():
        fixes.notes.append("The complexity analysis was discarded because it was not usable.")
        return trivial_complexity(analysis, fixes)
    real = {f.name: f for f in analysis.functions}
    functions: list[FunctionComplexity] = []
    for f in c.functions:
        span = clamp_lines(f.start_line, f.end_line, total)
        worst, f_space = clean_big_o(f.worst_case), clean_big_o(f.space)
        if span is None or worst is None or f_space is None or not f.name.strip():
            fixes.dropped_other += 1
            continue
        if not name_in_code(f.name, code):
            fixes.dropped_names += 1  # the model invented (or renamed) this function
            continue
        start, end = span
        known = real.get(f.name.strip().split(".")[-1])
        if known is not None:  # the real line range beats the model's guess
            start, end = known.start_line, known.end_line
        functions.append(
            FunctionComplexity(
                name=f.name.strip(),
                start_line=start,
                end_line=end or start,
                best_case=clean_big_o(f.best_case),
                average_case=clean_big_o(f.average_case),
                worst_case=worst,
                space=f_space,
                explanation=f.explanation.strip() or "No explanation given.",
            )
        )
    return Complexity(
        time=time, space=space, explanation=c.explanation.strip(), functions=functions
    )


def trivial_complexity(analysis: StaticAnalysis, fixes: Corrections) -> Complexity | None:
    """O(1) for code with no loops, no recursion and no calls: a case the model sometimes skips.

    Anything less obvious is left to the model; this never guesses.
    """
    if not (analysis.parsed and analysis.functions and analysis.only_definitions):
        return None
    if any(f.loop_depth or f.self_calls or f.has_calls for f in analysis.functions):
        return None
    why = (
        "it has no loops, no recursion and no calls, so the work does not depend on the input size"
    )
    fixes.notes.append("The complexity was worked out by reading the code, not by the model.")
    return Complexity(
        time="O(1)",
        space="O(1)",
        explanation=f"Constant time and space: {why}.",
        functions=[
            FunctionComplexity(
                name=f.name,
                start_line=f.start_line,
                end_line=f.end_line,
                best_case=None,
                average_case=None,
                worst_case="O(1)",
                space="O(1)",
                explanation="No loops, recursion or calls.",
            )
            for f in analysis.functions
        ],
    )


def _alternatives(entry: CatalogEntry) -> list[AlgorithmAlternative]:
    return [
        AlgorithmAlternative(name=a.name, time=a.time, space=a.space, tradeoff=a.tradeoff)
        for a in entry.alternatives
    ]


def convert_algorithms(
    raw: LlmReview, lines: list[str], analysis: StaticAnalysis, fixes: Corrections
) -> list[DetectedAlgorithm]:
    result: list[DetectedAlgorithm] = []
    used: set[str] = set()

    # 1. Recognised by the structure of the code: certain, and described from the catalogue.
    for found in analysis.algorithms:
        if found.key in used:
            continue
        used.add(found.key)
        known = CATALOG[found.key]
        result.append(
            DetectedAlgorithm(
                name=known.name,
                category=known.category,
                confidence="high",
                start_line=found.start_line,
                end_line=found.end_line,
                evidence=code_at(lines, found.start_line, found.end_line),
                summary=known.summary,
                time=known.time,
                space=known.space,
                assessment=known.assessment,
                alternatives=_alternatives(known),
            )
        )

    # 2. Named by the model: kept only if the code backs it up.
    for a in raw.algorithms:
        entry = find_entry(a.name)
        if entry is not None and entry.key in used:
            continue  # already listed above
        claims_caching = re.search(r"dynamic|memo", f"{a.name} {a.category}", re.IGNORECASE)
        if claims_caching and analysis.parsed and not analysis.has_memoization:
            fixes.dropped_algorithms += 1  # plain recursion is not dynamic programming
            continue
        span = clamp_lines(a.start_line, a.end_line, len(lines))
        time, space = clean_big_o(a.time), clean_big_o(a.space)
        needed = (a.name.strip(), a.category.strip(), a.summary.strip())
        if span is None or time is None or space is None or not all(needed):
            fixes.dropped_other += 1
            continue
        # Models often describe the algorithm instead of quoting code, so a loose match is
        # enough; a claim that matches nothing near where it says is dropped.
        if anchor_evidence(a.evidence, lines, span[0], span[1]) is None:
            fixes.dropped_algorithms += 1
            continue
        start, end = span
        confidence = a.confidence
        if entry is not None and analysis.parsed:
            # For Python the structural checks are authoritative: a named algorithm they did not
            # confirm is shown as a low-confidence claim, with the model's own figures.
            entry, confidence = None, "low"
        if entry is not None:  # a standard algorithm: use the standard figures
            used.add(entry.key)
            name, category, time, space = entry.name, entry.category, entry.time, entry.space
            summary, assessment, alternatives = (
                entry.summary,
                entry.assessment,
                _alternatives(entry),
            )
        else:
            name, category = a.name.strip()[:80], a.category.strip()[:40]
            summary, assessment = a.summary.strip(), a.assessment.strip() or "No assessment given."
            alternatives = []
            for alt in a.alternatives:
                alt_time, alt_space = clean_big_o(alt.time), clean_big_o(alt.space)
                if alt_time and alt_space and alt.name.strip() and alt.tradeoff.strip():
                    alternatives.append(
                        AlgorithmAlternative(
                            name=alt.name.strip(),
                            time=alt_time,
                            space=alt_space,
                            tradeoff=alt.tradeoff.strip(),
                        )
                    )
        result.append(
            DetectedAlgorithm(
                name=name,
                category=category,
                confidence=confidence,
                start_line=start,
                end_line=end or start,
                evidence=code_at(lines, start, end or start),
                summary=summary,
                time=time,
                space=space,
                assessment=assessment,
                alternatives=alternatives,
            )
        )
    return result


def area_score(area: LlmArea, issues: list[CodeIssue], name: str) -> AreaScore:
    """The model's score, capped by what was actually found in that area.

    Each confident error takes 4 points off the ceiling and each confident warning 2; findings
    with low confidence count half. So a review cannot praise an area it also found errors in.
    """
    penalty = 0.0
    for issue in issues:
        if AREA_OF_CATEGORY[issue.category] != name:
            continue
        weight = {"error": 4.0, "warning": 2.0, "info": 0.5, "suggestion": 0.0}[issue.severity]
        penalty += weight * (0.5 if issue.confidence == "low" else 1.0)
    ceiling = max(1, round(10 - penalty))
    score = max(1, min(10, area.score, ceiling))
    return AreaScore(score=score, reason=area.reason.strip() or "No reason given.")


def overall_score(breakdown: ScoreBreakdown, issues: list[CodeIssue]) -> int:
    """A weighted average, never better than the worst problem allows.

    The average alone is too kind: one serious flaw barely moves it. So the score is capped by the
    weakest area (+3), by any error (5, or 4 for a security error), and by the number of warnings.
    """
    weighted = 0.0
    for name, weight in AREA_WEIGHTS.items():
        weighted += float(getattr(breakdown, name).score) * weight
    caps = [10, min_area(breakdown) + 3]
    errors = [i for i in issues if i.severity == "error"]
    if errors:
        caps.append(4 if any(i.category == "security" for i in errors) else 5)
    warnings = [i for i in issues if i.severity == "warning"]
    if len(warnings) >= 3:
        caps.append(7)
    elif warnings:
        caps.append(8)
    return max(1, min(round(weighted), *caps))


def min_area(breakdown: ScoreBreakdown) -> int:
    return int(min(getattr(breakdown, name).score for name in AREA_WEIGHTS))


def verdict_for(score: int, issues: list[CodeIssue], weakest_area: int = 10) -> Verdict:
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    if errors:
        return "fix-before-use"
    if len(warnings) >= 2 or score <= 5 or weakest_area <= 3:
        return "needs-work"
    if warnings or score < 9:
        return "mostly-fine"
    return "looks-good"


def build_result(raw: LlmReview, code: str, language: Language = "python") -> ReviewResult:
    """The whole conversion. Raises ValueError if even the cleaned data is not a valid review."""
    lines = code.splitlines()
    fixes = Corrections()
    analysis = analyse(code) if language == "python" else StaticAnalysis()

    issues = convert_issues(raw.issues, lines, fixes, analysis if language == "python" else None)
    complexity = convert_complexity(raw, code, analysis, fixes)
    algorithms = convert_algorithms(raw, lines, analysis, fixes)
    positives = [
        Positive(line=p.line, comment=p.comment.strip())
        for p in raw.positives
        if 1 <= p.line <= len(lines) and p.comment.strip()
    ][:MAX_POSITIVES]

    breakdown = ScoreBreakdown(
        correctness=area_score(raw.area_scores.correctness, issues, "correctness"),
        security=area_score(raw.area_scores.security, issues, "security"),
        performance=area_score(raw.area_scores.performance, issues, "performance"),
        readability=area_score(raw.area_scores.readability, issues, "readability"),
    )
    score = overall_score(breakdown, issues)
    weakest = min_area(breakdown)

    metrics = measure(code)
    if analysis.parsed:
        metrics = metrics.model_copy(
            update={
                "function_count": len(analysis.functions),
                "longest_function_lines": analysis.longest_function_lines,
                "max_nesting_depth": analysis.max_nesting_depth,
            }
        )

    limitations = [text.strip() for text in raw.limitations if text.strip()]
    for name in AREA_WEIGHTS:
        rated = getattr(breakdown, name).score
        has_finding = any(AREA_OF_CATEGORY[i.category] == name for i in issues)
        if rated <= 5 and not has_finding:
            limitations.append(
                f"The model rated {name} {rated}/10 but gave no specific finding that could be "
                "verified, so treat that rating with care."
            )
    if fixes.rule_findings:
        limitations.append(
            f"{fixes.rule_findings} finding(s) come from rule-based checks of the code, "
            "not from the AI model."
        )
    if fixes.dropped_issues:
        limitations.append(
            f"{fixes.dropped_issues} finding(s) were removed because the code they quoted "
            "could not be found in your snippet."
        )
    if fixes.repaired_evidence:
        limitations.append(
            f"{fixes.repaired_evidence} finding(s) quoted the code slightly wrongly; "
            "the real code is shown instead."
        )
    if fixes.moved_issues:
        limitations.append(f"{fixes.moved_issues} finding(s) had their line number corrected.")
    if fixes.downgraded_issues:
        limitations.append(
            f"{fixes.downgraded_issues} finding(s) were shown with a milder severity than the "
            "model gave (low confidence, or a style remark)."
        )
    if fixes.dropped_algorithms:
        limitations.append(
            f"{fixes.dropped_algorithms} algorithm claim(s) were removed because the code does "
            "not support them."
        )
    if fixes.dropped_names:
        limitations.append(
            f"{fixes.dropped_names} function(s) in the complexity table were removed because "
            "no function with that name exists in your code."
        )
    limitations.extend(fixes.notes)
    if language != "python":
        limitations.append(
            "Rule-based checks currently cover Python only; for this language every finding "
            "comes from the AI model."
        )
    limitations.append(
        "Findings and complexity figures that come from the AI model were checked against the "
        "text of your code but not proven; treat them as a strong hint."
    )

    return ReviewResult(
        purpose=raw.purpose.strip() or "Not stated.",
        summary=raw.summary.strip() or "No summary given.",
        verdict=verdict_for(score, issues, weakest),
        score=score,
        score_breakdown=breakdown,
        priority_fixes=[i.id for i in issues if i.severity in ("error", "warning")][:3],
        issues=issues,
        positives=positives,
        complexity=complexity,
        algorithms=algorithms,
        metrics=metrics,
        limitations=limitations,
    )
