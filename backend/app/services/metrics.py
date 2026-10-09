"""Facts measured directly from the code (no AI involved)."""

from app.schemas import Metrics

# A line that starts with one of these (after indentation) counts as a comment line.
COMMENT_PREFIXES = ("//", "#", "/*", "*", "*/")


def measure(code: str) -> Metrics:
    """Line counts. Function counts and nesting need a parser and are left as None for now."""
    lines = code.splitlines()
    blank = sum(1 for line in lines if not line.strip())
    comments = sum(1 for line in lines if line.strip().startswith(COMMENT_PREFIXES))
    return Metrics(
        total_lines=len(lines),
        code_lines=len(lines) - blank - comments,
        comment_lines=comments,
        blank_lines=blank,
        longest_line=max((len(line) for line in lines), default=0),
    )
