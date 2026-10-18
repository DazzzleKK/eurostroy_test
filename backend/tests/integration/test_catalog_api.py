"""HTTP-контракт каталога на фейковом контейнере."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from eurostroy.api.app import create_app
from eurostroy.api.deps import get_container
from eurostroy.config import Settings
from tests.fakes import JPEG_BYTES, PNG_BYTES
from tests.integration.fake_container import FakeContainer


@pytest.fixture
def container() -> FakeContainer:
    return FakeContainer()


@pytest.fixture
def client(container: FakeContainer) -> Iterator[TestClient]:
    app = create_app(Settings(bot_token=""))
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed(container: FakeContainer, count: int, payload: bytes = JPEG_BYTES) -> None:
    async def run() -> None:
        async with container.product_commands() as use_case:
            for index in range(count):
                await use_case.execute(title=f"Товар {index + 1}", image_bytes=payload)

    asyncio.run(run())


def test_empty_catalog(client: TestClient) -> None:
    response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == {"items": [], "next_cursor": None}


def test_catalog_lists_newest_first(client: TestClient, container: FakeContainer) -> None:
    seed(container, 2)

    response = client.get("/api/products")

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["items"]] == ["Товар 2", "Товар 1"]
    assert body["next_cursor"] is None
    assert body["items"][0]["image_url"] == f"/api/products/{body['items'][0]['id']}/image"


def test_catalog_pages_with_cursor(client: TestClient, container: FakeContainer) -> None:
    seed(container, 3)

    first = client.get("/api/products", params={"limit": 2}).json()
    second = client.get(
        "/api/products",
        params={"limit": 2, "cursor": first["next_cursor"]},
    ).json()

    assert len(first["items"]) == 2
    assert first["next_cursor"] is not None
    assert len(second["items"]) == 1
    assert second["next_cursor"] is None
    assert set(first["items"][0]) == {"id", "title", "image_url", "created_at"}


@pytest.mark.parametrize("limit", [0, 101, -5])
def test_limit_out_of_range_returns_422(client: TestClient, limit: int) -> None:
    assert client.get("/api/products", params={"limit": limit}).status_code == 422


def test_broken_cursor_returns_domain_error(client: TestClient) -> None:
    response = client.get("/api/products", params={"cursor": "broken"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_failed"


def test_image_is_served_with_cache_header(client: TestClient, container: FakeContainer) -> None:
    seed(container, 1, payload=PNG_BYTES)
    product_id = container.repository.rows[0].id

    response = client.get(f"/api/products/{product_id}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.content == PNG_BYTES


def test_missing_product_image_returns_404(client: TestClient) -> None:
    response = client.get(f"/api/products/{UUID(int=999)}/image")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "product_not_found"


def test_healthz_reports_dependencies(client: TestClient) -> None:
    response = client.get("/api/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": True, "storage": True}
