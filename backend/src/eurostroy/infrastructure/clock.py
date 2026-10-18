"""Часы и генератор идентификаторов.

Вынесены в порты, чтобы usecase не вызывал ``datetime.now`` и ``uuid4``
напрямую: иначе тесты на курсоры и ключи объектов зависят от реального времени.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class Uuid4Factory:
    def new_product_id(self) -> UUID:
        return uuid4()
