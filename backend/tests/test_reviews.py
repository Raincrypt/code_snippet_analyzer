from uuid import uuid4

from httpx import AsyncClient

from tests.conftest import SAMPLE_CODE


async def test_create_review_returns_a_saved_review(client: AsyncClient) -> None:
    response = await client.post("/api/reviews", json={"code": SAMPLE_CODE, "language": "python"})
    assert response.status_code == 201
    body = response.json()
    assert body["language"] == "python"
    assert body["code"] == SAMPLE_CODE
    assert body["reviewer"] == "stub"
    assert body["messages"] == []
    assert body["createdAt"].endswith("Z") or "+00:00" in body["createdAt"]
    assert 1 <= body["result"]["score"] <= 10


async def test_review_json_is_camel_case_like_the_frontend(review: dict[str, object]) -> None:
    assert {"createdAt", "promptVersion", "tokensIn", "latencyMs"} <= review.keys()
    assert "created_at" not in review


async def test_create_review_rejects_blank_code(client: AsyncClient) -> None:
    response = await client.post("/api/reviews", json={"code": "   \n", "language": "python"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_create_review_rejects_unknown_language(client: AsyncClient) -> None:
    response = await client.post("/api/reviews", json={"code": "x", "language": "cobol"})
    assert response.status_code == 422
    fields = [d["field"] for d in response.json()["error"]["details"]]
    assert "language" in fields


async def test_create_review_rejects_oversized_code(client: AsyncClient, settings) -> None:  # type: ignore[no-untyped-def]
    too_long = "x" * (settings.max_code_chars + 1)
    response = await client.post("/api/reviews", json={"code": too_long, "language": "python"})
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


async def test_get_review_returns_what_was_saved(
    client: AsyncClient, review: dict[str, object]
) -> None:
    response = await client.get(f"/api/reviews/{review['id']}")
    assert response.status_code == 200
    assert response.json() == review


async def test_get_unknown_review_is_404(client: AsyncClient) -> None:
    response = await client.get(f"/api/reviews/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_malformed_review_id_is_a_validation_error(client: AsyncClient) -> None:
    response = await client.get("/api/reviews/not-a-uuid")
    assert response.status_code == 422


async def test_list_is_newest_first_with_totals(client: AsyncClient) -> None:
    for code in ("first", "second", "third"):
        await client.post("/api/reviews", json={"code": code, "language": "go"})

    page = (await client.get("/api/reviews", params={"limit": 2})).json()
    assert page["total"] == 3
    assert page["limit"] == 2
    assert [item["preview"] for item in page["items"]] == ["third", "second"]

    rest = (await client.get("/api/reviews", params={"limit": 2, "offset": 2})).json()
    assert [item["preview"] for item in rest["items"]] == ["first"]


async def test_list_items_summarise_the_result(
    client: AsyncClient, review: dict[str, object]
) -> None:
    item = (await client.get("/api/reviews")).json()["items"][0]
    assert item["id"] == review["id"]
    assert item["language"] == "python"
    assert item["issueCount"] == len(review["result"]["issues"])  # type: ignore[index,arg-type]
    assert "code" not in item


async def test_list_validates_paging_parameters(client: AsyncClient) -> None:
    assert (await client.get("/api/reviews", params={"limit": 0})).status_code == 422
    assert (await client.get("/api/reviews", params={"limit": 101})).status_code == 422
    assert (await client.get("/api/reviews", params={"offset": -1})).status_code == 422


async def test_delete_removes_the_review(client: AsyncClient, review: dict[str, object]) -> None:
    assert (await client.delete(f"/api/reviews/{review['id']}")).status_code == 204
    assert (await client.get(f"/api/reviews/{review['id']}")).status_code == 404
    assert (await client.delete(f"/api/reviews/{review['id']}")).status_code == 404
