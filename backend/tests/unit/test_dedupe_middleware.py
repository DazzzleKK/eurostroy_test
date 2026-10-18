"""Идемпотентность апдейтов: middleware не пускает дубли в хендлеры."""

from __future__ import annotations

from typing import Any

import pytest
from aiogram.types import TelegramObject, Update

from eurostroy.infrastructure.telegram.middleware import DedupeMiddleware, UpdateIsBusy


class FakeDeduplicator:
    def __init__(self, *, allow: bool, finished: bool = False) -> None:
        self.allow = allow
        self.finished = finished
        self.claimed: list[int] = []
        self.done: list[int] = []
        self.released: list[int] = []

    async def claim(self, update_id: int) -> bool:
        self.claimed.append(update_id)
        return self.allow

    async def is_done(self, update_id: int) -> bool:
        return self.finished

    async def mark_done(self, update_id: int) -> None:
        self.done.append(update_id)

    async def release(self, update_id: int) -> None:
        self.released.append(update_id)


def make_update(update_id: int) -> Update:
    return Update(update_id=update_id)


async def test_first_delivery_reaches_handler() -> None:
    deduplicator = FakeDeduplicator(allow=True)
    seen: list[int] = []

    async def handler(event: TelegramObject, data: dict[str, Any]) -> str:
        assert isinstance(event, Update)
        seen.append(event.update_id)
        return "handled"

    result = await DedupeMiddleware(deduplicator)(handler, make_update(42), {})

    assert result == "handled"
    assert seen == [42]
    assert deduplicator.done == [42]
    assert deduplicator.released == []


async def test_duplicate_of_finished_update_is_dropped() -> None:
    deduplicator = FakeDeduplicator(allow=False, finished=True)
    seen: list[int] = []

    async def handler(event: TelegramObject, data: dict[str, Any]) -> None:
        seen.append(1)

    result = await DedupeMiddleware(deduplicator)(handler, make_update(7), {})

    assert result is None
    assert seen == []
    assert deduplicator.done == []


async def test_update_in_progress_asks_for_retry() -> None:
    deduplicator = FakeDeduplicator(allow=False, finished=False)

    async def handler(event: TelegramObject, data: dict[str, Any]) -> None:
        raise AssertionError("handler must not run for an update in progress")

    with pytest.raises(UpdateIsBusy):
        await DedupeMiddleware(deduplicator)(handler, make_update(8), {})


async def test_failure_releases_claim_for_retry() -> None:
    deduplicator = FakeDeduplicator(allow=True)

    async def handler(event: TelegramObject, data: dict[str, Any]) -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await DedupeMiddleware(deduplicator)(handler, make_update(9), {})

    assert deduplicator.released == [9]
    assert deduplicator.done == []
