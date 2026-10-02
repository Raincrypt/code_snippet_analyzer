from httpx import AsyncClient


async def test_health_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0", "reviewer": "stub"}


async def test_ready_checks_the_database(client: AsyncClient) -> None:
    response = await client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_unknown_route_uses_the_error_shape(client: AsyncClient) -> None:
    response = await client.get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_response_carries_a_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert len(response.headers["x-request-id"]) >= 8


async def test_a_safe_request_id_is_echoed(client: AsyncClient) -> None:
    response = await client.get("/api/health", headers={"X-Request-ID": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


async def test_an_unsafe_request_id_is_replaced(client: AsyncClient) -> None:
    response = await client.get("/api/health", headers={"X-Request-ID": "bad id\twith spaces"})
    assert response.headers["x-request-id"] != "bad id\twith spaces"


async def test_error_bodies_include_the_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/nope", headers={"X-Request-ID": "trace-9"})
    assert response.json()["error"]["requestId"] == "trace-9"


async def test_docs_are_available_outside_production(client: AsyncClient) -> None:
    assert (await client.get("/api/docs")).status_code == 200
