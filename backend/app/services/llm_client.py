"""Talks to a model server over the OpenAI-compatible chat API (Ollama, vLLM, LM Studio, hosted).

Only this file knows the wire format. The reviewer above it deals in plain messages and text, so
switching servers (or adding another kind of client later) does not touch the review logic.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.services.reviewer import ReviewerError

logger = logging.getLogger(__name__)

Message = dict[str, str]
# Called with each piece of text as the model produces it.
TextCallback = Callable[[str], Awaitable[None]]


class LlmError(ReviewerError):
    """Base class: the model server could not give a usable reply."""


class LlmUnavailableError(LlmError):
    """The server cannot be reached, or the model is not installed."""

    public_message = "The AI model is not available right now. Please try again in a moment."


class LlmTimeoutError(LlmError):
    """The server took too long."""

    public_message = "The AI model took too long to answer. Try a shorter snippet."


class LlmBadReplyError(LlmError):
    """The server answered, but the reply cannot be used (cut off, empty, not JSON, wrong shape)."""

    public_message = "The AI model gave an answer that could not be used. Please try again."


@dataclass(frozen=True)
class Completion:
    text: str
    finish_reason: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None


class LlmClient(Protocol):
    model: str

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        on_text: TextCallback | None = None,
    ) -> Completion: ...

    async def list_models(self) -> list[str]: ...


class OpenAICompatibleClient:
    RETRIES = 2  # extra attempts for connection failures and 502/503/504, before any text arrives
    RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 300.0,
        temperature: float = 0.1,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._transport = transport
        # Waiting for the first token can take a while (the model loads, the prompt is read);
        # after that, tokens should keep flowing.
        self._timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=self._timeout, headers=self._headers, transport=self._transport
        )

    async def list_models(self) -> list[str]:
        try:
            async with self._http() as http:
                response = await http.get(f"{self.base_url}/models")
            response.raise_for_status()
            # Ollama sends "data": null when no model is installed yet.
            return [str(m["id"]) for m in (response.json().get("data") or [])]
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise LlmUnavailableError("The model server could not be reached.") from exc

    async def complete(
        self,
        messages: list[Message],
        *,
        max_tokens: int,
        json_schema: dict[str, Any] | None = None,
        on_text: TextCallback | None = None,
    ) -> Completion:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "review", "strict": True, "schema": json_schema},
            }

        last_error: LlmError | None = None
        for attempt in range(self.RETRIES + 1):
            received_text = False

            async def forward(piece: str) -> None:
                nonlocal received_text
                received_text = True
                if on_text is not None:
                    await on_text(piece)

            try:
                return await self._stream(body, forward)
            except LlmUnavailableError as exc:
                last_error = exc
                retryable = not received_text and exc.__cause__ is not None
            except LlmTimeoutError:
                raise  # retrying would only double a wait that was already long
            if not retryable or attempt == self.RETRIES:
                break
            logger.warning("model server call failed, retrying (attempt %d)", attempt + 1)
            await asyncio.sleep(self.RETRY_DELAY_SECONDS * (attempt + 1))
        assert last_error is not None
        raise last_error

    async def _stream(self, body: dict[str, Any], on_text: TextCallback) -> Completion:
        parts: list[str] = []
        finish_reason: str | None = None
        tokens_in: int | None = None
        tokens_out: int | None = None
        try:
            async with (
                self._http() as http,
                http.stream("POST", f"{self.base_url}/chat/completions", json=body) as response,
            ):
                if response.status_code >= 400:
                    detail = (await response.aread()).decode("utf-8", "replace")[:300]
                    self._raise_for_status(response.status_code, detail)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    if usage := chunk.get("usage"):
                        tokens_in = usage.get("prompt_tokens")
                        tokens_out = usage.get("completion_tokens")
                    for choice in chunk.get("choices") or []:
                        piece = (choice.get("delta") or {}).get("content")
                        if piece:
                            parts.append(piece)
                            await on_text(piece)
                        if choice.get("finish_reason"):
                            finish_reason = choice["finish_reason"]
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("The model took too long to answer.") from exc
        except httpx.HTTPError as exc:
            raise LlmUnavailableError("The model server could not be reached.") from exc
        return Completion("".join(parts), finish_reason, tokens_in, tokens_out)

    def _raise_for_status(self, status: int, detail: str) -> None:
        logger.warning("model server returned %d: %s", status, detail)
        if status == 404:
            raise LlmUnavailableError(f"The model '{self.model}' is not available on the server.")
        error = LlmUnavailableError(f"The model server returned an error ({status}).")
        if status in (502, 503, 504):
            # Raised "from" something so the retry logic treats it as transient.
            raise error from httpx.HTTPStatusError(
                detail,
                request=httpx.Request("POST", self.base_url),
                response=httpx.Response(status),
            )
        raise error
