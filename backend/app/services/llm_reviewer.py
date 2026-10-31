"""The reviewer that asks a language model. Plugs in behind the same `Reviewer` protocol as the
placeholder, so the API, database and frontend are unchanged.

One review is one model call (made in a way the model's output must match `LlmReview`), followed
by plain-code checks in `postprocess.py`. If the reply is not valid, the model gets one chance to
correct it.
"""

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.config import Settings
from app.prompts import chat_v1, review_v2
from app.schemas import Language, ReviewStage
from app.services.llm_client import (
    Completion,
    LlmBadReplyError,
    LlmClient,
    LlmError,
    Message,
    OpenAICompatibleClient,
)
from app.services.llm_schema import LlmReview
from app.services.postprocess import build_result
from app.services.reviewer import (
    AnswerOutcome,
    AnswerRequest,
    ProgressCallback,
    ReviewOutcome,
)

logger = logging.getLogger(__name__)

HISTORY_TURNS = 6  # how many earlier chat messages are sent along with a question
# The model writes fields in schema order, so seeing a field name tells us how far it has got.
STAGE_MARKERS: tuple[tuple[ReviewStage, str], ...] = (
    ("analyse", '"issues"'),
    ("complexity", '"complexity"'),
)


def extract_json(text: str) -> str:
    """The JSON object inside a reply, tolerating code fences and stray words around it."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("The reply contained no JSON object.")
    return text[start : end + 1]


def describe_errors(error: Exception) -> str:
    """A short list of what was wrong, to show the model when asking it to try again."""
    if isinstance(error, ValidationError):
        lines = [
            f"- {'.'.join(str(p) for p in e['loc']) or 'reply'}: {e['msg']}"
            for e in error.errors()[:8]
        ]
        return "\n".join(lines)
    return f"- {error}"


class LlmReviewer:
    name = "llm"

    def __init__(
        self,
        client: LlmClient,
        *,
        max_output_tokens: int = 4096,
        max_concurrency: int = 1,
    ) -> None:
        self.client = client
        self.max_output_tokens = max_output_tokens
        # Limits simultaneous model calls; others wait their turn.
        self._slots = asyncio.Semaphore(max_concurrency)
        self._schema: dict[str, Any] = LlmReview.model_json_schema()

    @property
    def model_name(self) -> str:
        return self.client.model

    async def check(self) -> dict[str, Any]:
        """Is the server up and is the configured model installed? (For the status endpoint.)"""
        try:
            models = await self.client.list_models()
        except LlmError:
            return {
                "ready": False,
                "state": "unreachable",
                "model": self.model_name,
                "detail": "Model server not reachable.",
            }
        # Ollama lists "qwen2.5-coder:7b"; a name without a tag means ":latest".
        wanted = {self.model_name, f"{self.model_name}:latest"}
        installed = any(m in wanted for m in models)
        return {
            "ready": installed,
            "state": "ready" if installed else "model-missing",
            "model": self.model_name,
            "detail": "Ready." if installed else "The model is not installed on the server.",
        }

    async def review(
        self, code: str, language: Language, progress: ProgressCallback | None = None
    ) -> ReviewOutcome:
        async def report(stage: ReviewStage) -> None:
            if progress is not None:
                await progress(stage)

        await report("prepare")
        messages: list[Message] = [
            {"role": "system", "content": review_v2.SYSTEM_PROMPT},
            {"role": "user", "content": review_v2.build_user_prompt(code, language)},
        ]

        async with self._slots:
            await report("understand")
            buffer: list[str] = []
            reached = 0  # how many STAGE_MARKERS have been seen

            async def watch(piece: str) -> None:
                nonlocal reached
                buffer.append(piece)
                text = "".join(buffer[-8:]) if reached else "".join(buffer)
                while reached < len(STAGE_MARKERS) and STAGE_MARKERS[reached][1] in text:
                    await report(STAGE_MARKERS[reached][0])
                    reached += 1

            first = await self.client.complete(
                messages,
                max_tokens=self.max_output_tokens,
                json_schema=self._schema,
                on_text=watch,
            )
            # Make sure every step was reported even if the model's field order was unusual.
            for stage, _ in STAGE_MARKERS[reached:]:
                await report(stage)

            parsed, completion = await self._parse(first, messages)

        await report("verify")
        try:
            result = build_result(parsed, code, language)
        except (ValidationError, ValueError) as exc:
            logger.warning("review failed final validation: %s", describe_errors(exc))
            raise LlmBadReplyError("The model's review could not be validated.") from exc

        return ReviewOutcome(
            result=result,
            model=self.model_name,
            prompt_version=review_v2.PROMPT_VERSION,
            tokens_in=_sum(first.tokens_in, completion.tokens_in, same=completion is first),
            tokens_out=_sum(first.tokens_out, completion.tokens_out, same=completion is first),
        )

    async def _parse(
        self, first: Completion, messages: list[Message]
    ) -> tuple[LlmReview, Completion]:
        """Reads the reply; if it is unusable, asks the model once to correct it."""
        try:
            return self._read(first), first
        except (ValidationError, ValueError) as exc:
            if first.finish_reason == "length":
                raise LlmBadReplyError(
                    "The model's answer was cut off. Try a shorter snippet."
                ) from exc
            problem = describe_errors(exc)
            logger.info("model reply invalid, asking for a correction: %s", problem)
            retry_messages = [
                *messages,
                {"role": "assistant", "content": first.text},
                {"role": "user", "content": review_v2.build_repair_prompt(problem)},
            ]
            second = await self.client.complete(
                retry_messages, max_tokens=self.max_output_tokens, json_schema=self._schema
            )
            try:
                return self._read(second), second
            except (ValidationError, ValueError) as exc2:
                logger.warning("model reply still invalid: %s", describe_errors(exc2))
                raise LlmBadReplyError("The model did not return a usable review.") from exc2

    @staticmethod
    def _read(completion: Completion) -> LlmReview:
        if not completion.text.strip():
            raise ValueError("The reply was empty.")
        return LlmReview.model_validate(json.loads(extract_json(completion.text)))

    async def answer(self, request: AnswerRequest) -> AnswerOutcome:
        messages: list[Message] = [
            {
                "role": "system",
                "content": chat_v1.build_system_prompt(
                    request.code, request.language, request.review, request.reply_style
                ),
            },
            *({"role": t.role, "content": t.content} for t in request.history[-HISTORY_TURNS:]),
            {"role": "user", "content": request.question},
        ]
        async with self._slots:
            completion = await self.client.complete(
                messages, max_tokens=chat_v1.MAX_TOKENS[request.reply_style]
            )
        text = completion.text.strip()
        if not text:
            raise LlmBadReplyError("The model returned an empty answer.")
        return AnswerOutcome(
            content=text,
            model=self.model_name,
            tokens_in=completion.tokens_in,
            tokens_out=completion.tokens_out,
        )


def _sum(a: int | None, b: int | None, *, same: bool) -> int | None:
    """Total tokens over the first call and (if there was one) the correction call."""
    if same:
        return a
    return None if a is None and b is None else (a or 0) + (b or 0)


def build_llm_reviewer(settings: Settings) -> LlmReviewer:
    client = OpenAICompatibleClient(
        settings.llm_base_url,
        settings.llm_model,
        api_key=settings.llm_api_key,
        timeout_seconds=settings.llm_timeout_seconds,
        temperature=settings.llm_temperature,
    )
    return LlmReviewer(
        client,
        max_output_tokens=settings.llm_max_output_tokens,
        max_concurrency=settings.llm_max_concurrency,
    )
