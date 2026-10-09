"""A built-in example, used by the stub reviewer so the app can be demonstrated end to end.

The sample code and its review live in `shared/demo/` at the repository root, where the frontend's
mock reads the same files. Both sides validate them against their own schema, so the two cannot
drift apart. When the folder is absent (for example in the Docker image) there is simply no demo.
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.schemas import ReviewResult

DEMO_DIR = Path(__file__).resolve().parents[3] / "shared" / "demo"


@dataclass(frozen=True)
class Demo:
    code: str
    review: ReviewResult


def _normalize(code: str) -> str:
    return code.replace("\r\n", "\n").strip()


@lru_cache
def load_demo() -> Demo | None:
    try:
        code = (DEMO_DIR / "sample-code.txt").read_text(encoding="utf-8")
        data = json.loads((DEMO_DIR / "review.json").read_text(encoding="utf-8"))
    except OSError:
        return None
    return Demo(code=_normalize(code), review=ReviewResult.model_validate(data))


def demo_review_for(code: str) -> ReviewResult | None:
    """The canned review if `code` is the built-in sample, otherwise None."""
    demo = load_demo()
    if demo is not None and _normalize(code) == demo.code:
        return demo.review
    return None
