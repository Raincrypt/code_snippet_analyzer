"""A tiny stand-in for Ollama, so the whole app can be tried without a model or a GPU.

    python evals/fake_model_server.py            # listens on :11500
    REVIEWER=llm LLM_BASE_URL=http://localhost:11500/v1 LLM_MODEL=fake uvicorn app.main:app

It answers the same OpenAI-style requests the real client sends, with a canned review that
quotes the first line of whatever code it was shown. It does NOT analyse anything.
"""

import asyncio
import json
import re
import sys

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()
DELAY = float(sys.argv[2]) if len(sys.argv) > 2 else 0.01


def canned_review(prompt: str) -> dict[str, object]:
    code_lines = re.findall(r"^\s*(\d+) \| (.*)$", prompt, re.MULTILINE)
    first = next(((int(n), t.strip()) for n, t in code_lines if t.strip()), (1, "x"))
    return {
        "purpose": "Demonstration reply from the fake model server.",
        "summary": "This is canned output; no model looked at your code.",
        "issues": [
            {
                "line": first[0],
                "end_line": None,
                "severity": "info",
                "category": "style",
                "title": "Canned finding on the first line",
                "explanation": "The fake server always reports its first non-blank line.",
                "impact": "None. This only shows how a real finding is displayed.",
                "evidence": first[1],
                "confidence": "low",
                "effort": "quick",
                "fix": None,
            }
        ],
        "positives": [],
        "complexity": {
            "time": "O(n)",
            "space": "O(1)",
            "explanation": "Canned figure: n is the number of lines.",
            "functions": [],
        },
        "algorithms": [],
        "area_scores": {
            "correctness": {"score": 8, "reason": "Canned."},
            "security": {"score": 8, "reason": "Canned."},
            "performance": {"score": 8, "reason": "Canned."},
            "readability": {"score": 8, "reason": "Canned."},
        },
        "limitations": ["Produced by the fake model server."],
    }


@app.get("/v1/models")
async def models() -> JSONResponse:
    return JSONResponse({"data": [{"id": "fake"}]})


@app.post("/v1/chat/completions")
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    prompt = "\n".join(m["content"] for m in body["messages"])
    wants_json = "response_format" in body
    text = json.dumps(canned_review(prompt)) if wants_json else "This is a canned chat answer."

    async def events():  # type: ignore[no-untyped-def]
        for i in range(0, len(text), 30):
            await asyncio.sleep(DELAY)
            chunk = {"choices": [{"delta": {"content": text[i : i + 30]}, "finish_reason": None}]}
            yield f"data: {json.dumps(chunk)}\n\n"
        yield f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        usage = {
            "choices": [],
            "usage": {"prompt_tokens": 500, "completion_tokens": len(text) // 4},
        }
        yield f"data: {json.dumps(usage)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, port=int(sys.argv[1]) if len(sys.argv) > 1 else 11500)
