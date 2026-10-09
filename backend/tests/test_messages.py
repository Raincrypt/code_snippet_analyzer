from uuid import uuid4

from httpx import AsyncClient


async def ask(client: AsyncClient, review_id: object, question: str = "Why?", style: str = "brief"):  # type: ignore[no-untyped-def]
    return await client.post(
        f"/api/reviews/{review_id}/messages", json={"question": question, "replyStyle": style}
    )


async def test_asking_saves_both_messages(client: AsyncClient, review: dict[str, object]) -> None:
    response = await ask(client, review["id"], "Why was line 1 flagged?")
    assert response.status_code == 201
    body = response.json()
    assert body["userMessage"]["role"] == "user"
    assert body["userMessage"]["content"] == "Why was line 1 flagged?"
    assert body["assistantMessage"]["role"] == "assistant"
    assert body["assistantMessage"]["replyStyle"] == "brief"


async def test_messages_appear_on_the_review_in_order(
    client: AsyncClient, review: dict[str, object]
) -> None:
    await ask(client, review["id"], "First?")
    await ask(client, review["id"], "Second?")
    detail = (await client.get(f"/api/reviews/{review['id']}")).json()
    assert [m["content"] for m in detail["messages"] if m["role"] == "user"] == [
        "First?",
        "Second?",
    ]
    assert len(detail["messages"]) == 4


async def test_reply_style_reaches_the_reviewer(
    client: AsyncClient, review: dict[str, object]
) -> None:
    brief = (await ask(client, review["id"], style="brief")).json()
    detailed = (await ask(client, review["id"], style="detailed")).json()
    assert "brief" in brief["assistantMessage"]["content"]
    assert "detailed" in detailed["assistantMessage"]["content"]


async def test_reply_style_defaults_to_brief(
    client: AsyncClient, review: dict[str, object]
) -> None:
    response = await client.post(f"/api/reviews/{review['id']}/messages", json={"question": "Hi"})
    assert response.json()["assistantMessage"]["replyStyle"] == "brief"


async def test_asking_about_an_unknown_review_is_404(client: AsyncClient) -> None:
    assert (await ask(client, uuid4())).status_code == 404


async def test_blank_question_is_rejected(client: AsyncClient, review: dict[str, object]) -> None:
    assert (await ask(client, review["id"], "   ")).status_code == 422


async def test_unknown_reply_style_is_rejected(
    client: AsyncClient, review: dict[str, object]
) -> None:
    assert (await ask(client, review["id"], style="shouty")).status_code == 422


async def test_oversized_question_is_rejected(
    client: AsyncClient,
    review: dict[str, object],
    settings,  # type: ignore[no-untyped-def]
) -> None:
    response = await ask(client, review["id"], "x" * (settings.max_question_chars + 1))
    assert response.status_code == 413
