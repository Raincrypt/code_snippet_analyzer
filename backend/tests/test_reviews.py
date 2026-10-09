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
    # The stub does not analyse arbitrary code, and says so instead of inventing findings.
    assert body["result"]["verdict"] == "not-assessed"
    assert body["result"]["score"] is None
    assert body["result"]["issues"] == []
    assert body["result"]["metrics"]["totalLines"] == 2


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


async def test_the_built_in_sample_gets_the_example_review(client: AsyncClient) -> None:
    from app.services.demo import DEMO_DIR

    sample = (DEMO_DIR / "sample-code.txt").read_text(encoding="utf-8")
    response = await client.post("/api/reviews", json={"code": sample, "language": "javascript"})
    result = response.json()["result"]
    assert result["verdict"] == "needs-work"
    assert result["complexity"]["time"] == "O(n²)"
    assert [a["name"] for a in result["algorithms"]][0] == "Bubble sort"
