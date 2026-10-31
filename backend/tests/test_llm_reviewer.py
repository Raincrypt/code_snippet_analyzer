import asyncio

import pytest

from app.schemas import ReviewStage
from app.services.llm_client import LlmBadReplyError, LlmUnavailableError
from app.services.llm_reviewer import LlmReviewer, extract_json
from app.services.reviewer import AnswerRequest, ChatTurn
from tests.llm_fakes import CODE, FakeClient, as_text, good_reply


async def run(client: FakeClient) -> tuple[object, list[ReviewStage]]:
    stages: list[ReviewStage] = []

    async def progress(stage: ReviewStage) -> None:
        stages.append(stage)

    outcome = await LlmReviewer(client).review(CODE, "python", progress)
    return outcome, stages


async def test_review_end_to_end_with_progress_and_metadata() -> None:
    client = FakeClient(as_text(good_reply()))
    outcome, stages = await run(client)
    assert stages == ["prepare", "understand", "analyse", "complexity", "verify"]
    assert outcome.model == "fake-model"  # type: ignore[attr-defined]
    assert outcome.prompt_version == "review_v2"  # type: ignore[attr-defined]
    assert (outcome.tokens_in, outcome.tokens_out) == (100, 50)  # type: ignore[attr-defined]
    assert outcome.result.issues[0].title == "Crashes on empty input"  # type: ignore[attr-defined]


async def test_prompt_contains_numbered_code_and_schema_is_sent() -> None:
    client = FakeClient(as_text(good_reply()))
    await run(client)
    user = client.calls[0][1]["content"]
    assert "1 | def largest(xs):" in user
    assert "2 |     best = xs[0]" in user
    assert client.schemas[0] is not None and "issues" in client.schemas[0]["properties"]


async def test_reply_wrapped_in_fences_is_accepted() -> None:
    client = FakeClient("Here you go:\n```json\n" + as_text(good_reply()) + "\n```")
    outcome, _ = await run(client)
    assert outcome.result.verdict == "fix-before-use"  # type: ignore[attr-defined]


async def test_invalid_reply_gets_one_correction_and_tokens_add_up() -> None:
    broken = good_reply()
    broken["issues"][0]["severity"] = "high"  # not an allowed value
    client = FakeClient(as_text(broken), as_text(good_reply()))
    outcome, _ = await run(client)
    assert len(client.calls) == 2
    repair = client.calls[1]
    assert repair[-2]["role"] == "assistant" and "severity" in repair[-1]["content"]
    assert (outcome.tokens_in, outcome.tokens_out) == (200, 100)  # type: ignore[attr-defined]


async def test_still_invalid_after_correction_fails_cleanly() -> None:
    client = FakeClient("not json at all", "still not json")
    with pytest.raises(LlmBadReplyError):
        await run(client)
    assert len(client.calls) == 2


async def test_cut_off_reply_is_not_retried() -> None:
    client = FakeClient('{"purpose": "x", "summ', finish_reason="length")
    with pytest.raises(LlmBadReplyError, match="cut off"):
        await run(client)
    assert len(client.calls) == 1


async def test_empty_reply_fails() -> None:
    with pytest.raises(LlmBadReplyError):
        await run(FakeClient("", ""))


async def test_server_errors_propagate() -> None:
    with pytest.raises(LlmUnavailableError):
        await run(FakeClient(LlmUnavailableError("down")))


async def test_concurrency_is_limited_to_one() -> None:
    running = 0
    peak = 0

    class Slow(FakeClient):
        async def complete(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            nonlocal running, peak
            running += 1
            peak = max(peak, running)
            await asyncio.sleep(0.02)
            running -= 1
            return await super().complete(*args, **kwargs)

    reviewer = LlmReviewer(Slow(*[as_text(good_reply())] * 3), max_concurrency=1)
    await asyncio.gather(*(reviewer.review(CODE, "python") for _ in range(3)))
    assert peak == 1


async def test_check_reports_model_installed_or_not() -> None:
    client = FakeClient()
    reviewer = LlmReviewer(client)
    first = await reviewer.check()
    assert first["ready"] is True and first["state"] == "ready"  # "fake-model:latest" counts
    client.models = ["other:7b"]
    status = await reviewer.check()
    assert status["ready"] is False and "not installed" in status["detail"]
    assert status["state"] == "model-missing"
    client.models = []
    down = await reviewer.check()
    assert down["ready"] is False and down["state"] == "unreachable"


async def test_answer_uses_style_history_and_review() -> None:
    client = FakeClient("Use a guard clause.")
    from app.schemas import ReviewResult
    from app.services.llm_schema import LlmReview
    from app.services.postprocess import build_result

    review: ReviewResult = build_result(LlmReview.model_validate(good_reply()), CODE)
    request = AnswerRequest(
        code=CODE,
        language="python",
        review=review,
        history=tuple(ChatTurn("user" if i % 2 == 0 else "assistant", f"m{i}") for i in range(10)),
        question="How do I fix it?",
        reply_style="brief",
    )
    outcome = await LlmReviewer(client).answer(request)
    assert outcome.content == "Use a guard clause."
    messages = client.calls[0]
    assert "1 to 3 sentences" in messages[0]["content"]
    assert "Crashes on empty input" in messages[0]["content"]
    assert [m["content"] for m in messages[1:]] == [f"m{i}" for i in range(4, 10)] + [
        "How do I fix it?"
    ]
    assert client.schemas[0] is None  # a chat answer is free text


def test_extract_json() -> None:
    assert extract_json('xx {"a": 1} yy') == '{"a": 1}'
    with pytest.raises(ValueError):
        extract_json("nothing here")
