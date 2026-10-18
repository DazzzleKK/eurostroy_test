"""Вебхук: проверка секрета и отказ без настроенного бота."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from eurostroy.api.app import create_app
from eurostroy.api.deps import get_container
from eurostroy.config import Settings
from tests.integration.fake_container import WEBHOOK_SECRET, FakeContainer


@pytest.fixture
def client(container: FakeContainer) -> Iterator[TestClient]:
    app = create_app(Settings(bot_token="", bot_webhook_secret=WEBHOOK_SECRET))
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def container() -> FakeContainer:
    return FakeContainer()


def test_webhook_requires_secret(client: TestClient) -> None:
    response = client.post("/api/telegram/webhook", json={"update_id": 1})

    assert response.status_code == 401


def test_webhook_rejects_wrong_secret(client: TestClient) -> None:
    response = client.post(
        "/api/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
    )

    assert response.status_code == 401


def test_webhook_reports_unconfigured_bot(client: TestClient) -> None:
    response = client.post(
        "/api/telegram/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "bot is not configured"


def test_webhook_accepts_valid_secret_when_bot_exists(
    client: TestClient, container: FakeContainer
) -> None:
    calls: list[int] = []

    class StubDispatcher:
        async def feed_update(self, bot: object, update: object) -> None:
            calls.append(1)

    container.bot = object()
    container.dispatcher = StubDispatcher()

    response = client.post(
        "/api/telegram/webhook",
        json={"update_id": 55},
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert calls == [1]


def test_webhook_drops_body_that_is_not_json(client: TestClient, container: FakeContainer) -> None:
    container.bot = object()

    class StubDispatcher:
        async def feed_update(self, bot: object, update: object) -> None:
            raise AssertionError("dispatcher must not be called for a broken body")

    container.dispatcher = StubDispatcher()

    response = client.post(
        "/api/telegram/webhook",
        content=b"not a json",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_webhook_asks_retry_when_update_is_busy(
    client: TestClient, container: FakeContainer
) -> None:
    from eurostroy.infrastructure.telegram.middleware import UpdateIsBusy

    container.bot = object()

    class BusyDispatcher:
        async def feed_update(self, bot: object, update: object) -> None:
            raise UpdateIsBusy(update_id=55)

    container.dispatcher = BusyDispatcher()

    response = client.post(
        "/api/telegram/webhook",
        json={"update_id": 55},
        headers={"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET},
    )

    assert response.status_code == 503
    assert response.headers["retry-after"] == "1"
