import json

import httpx
import pytest

from app.services.llm_client import (
    LlmTimeoutError,
    LlmUnavailableError,
    OpenAICompatibleClient,
)


def sse(*chunks: object) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks] + ["data: [DONE]\n\n"]
    return "".join(lines).encode()


def delta(text: str) -> dict[str, object]:
    return {"choices": [{"delta": {"content": text}, "finish_reason": None}]}


STREAM = sse(
    delta('{"a"'),
    delta(": 1}"),
    {"choices": [{"delta": {}, "finish_reason": "stop"}]},
    {"choices": [], "usage": {"prompt_tokens": 12, "completion_tokens": 3}},
)


def client_for(handler: object) -> OpenAICompatibleClient:
    c = OpenAICompatibleClient(
        "http://llm/v1",
        "m",
        api_key="secret",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )
    c.RETRY_DELAY_SECONDS = 0
    return c


async def test_streams_text_usage_and_sends_schema_and_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        return httpx.Response(200, content=STREAM)

    pieces: list[str] = []

    async def collect(piece: str) -> None:
        pieces.append(piece)

    result = await client_for(handler).complete(
        [{"role": "user", "content": "hi"}],
        max_tokens=100,
        json_schema={"type": "object"},
        on_text=collect,
    )
    assert pieces == ['{"a"', ": 1}"]
    assert (result.text, result.finish_reason) == ('{"a": 1}', "stop")
    assert (result.tokens_in, result.tokens_out) == (12, 3)
    body: dict[str, object] = seen["body"]  # type: ignore[assignment]
    assert body["stream"] is True and body["max_tokens"] == 100 and body["model"] == "m"
    assert body["response_format"]["json_schema"]["schema"] == {"type": "object"}  # type: ignore[index]
    assert seen["auth"] == "Bearer secret"
    assert seen["url"] == "http://llm/v1/chat/completions"


async def test_no_schema_means_no_response_format() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(200, content=STREAM)

    await client_for(handler).complete([], max_tokens=10)
    assert "response_format" not in bodies[0]


async def test_ignores_garbage_lines() -> None:
    content = b": comment\n\ndata: not json\n\n" + STREAM
    result = await client_for(lambda r: httpx.Response(200, content=content)).complete(
        [], max_tokens=10
    )
    assert result.text == '{"a": 1}'


async def test_missing_model_is_a_clear_error_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, json={"error": "model not found"})

    with pytest.raises(LlmUnavailableError, match="not available"):
        await client_for(handler).complete([], max_tokens=10)
    assert calls == 1


async def test_transient_server_error_is_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503) if calls < 3 else httpx.Response(200, content=STREAM)

    result = await client_for(handler).complete([], max_tokens=10)
    assert calls == 3 and result.text == '{"a": 1}'


async def test_connection_failure_is_retried_then_reported() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("refused")

    with pytest.raises(LlmUnavailableError, match="could not be reached"):
        await client_for(handler).complete([], max_tokens=10)
    assert calls == 3


async def test_other_errors_are_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    with pytest.raises(LlmUnavailableError):
        await client_for(handler).complete([], max_tokens=10)
    assert calls == 1


async def test_timeout_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("slow")

    with pytest.raises(LlmTimeoutError):
        await client_for(handler).complete([], max_tokens=10)
    assert calls == 1


async def test_list_models() -> None:
    handler = lambda r: httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b:7b"}]})  # noqa: E731
    assert await client_for(handler).list_models() == ["a", "b:7b"]
    with pytest.raises(LlmUnavailableError):
        await client_for(lambda r: httpx.Response(500)).list_models()
