"""Server-Sent Events formatting."""

import json
from typing import Any


def format_event(event: str, data: Any) -> str:
    """One SSE message. `data` is JSON on a single line, so it can never break the framing."""
    return (
        f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'), ensure_ascii=False)}\n\n"
    )


def format_raw_event(event: str, json_text: str) -> str:
    """Like `format_event` for text that is already compact JSON (for example a Pydantic dump)."""
    if "\n" in json_text or "\r" in json_text:
        raise ValueError("SSE data must be a single line")
    return f"event: {event}\ndata: {json_text}\n\n"


KEEP_ALIVE = ": keep-alive\n\n"  # a comment line; clients ignore it, proxies see traffic
