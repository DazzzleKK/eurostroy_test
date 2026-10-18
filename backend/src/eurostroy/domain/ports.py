"""Порты домена.

Слой application зависит от этих протоколов, а инфраструктура их реализует.
Поэтому usecase можно тестировать без PostgreSQL, MinIO и Telegram.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from eurostroy.domain.product import Product


class ProductRepository(Protocol):
    async def add(self, product: Product) -> None: ...

    async def get(self, product_id: UUID) -> Product | None: ...

    async def list_page(
        self,
        *,
        limit: int,
        before: tuple[datetime, UUID] | None,
    ) -> list[Product]:
        """Страница товаров от новых к старым, без учёта ``before`` строки."""
        ...


class ImageStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_product_id(self) -> UUID: ...


class UpdateDeduplicator(Protocol):
    """Идемпотентность вебхука: один и тот же ``update_id`` не обрабатывается дважды."""

    async def claim(self, update_id: int) -> bool: ...

    async def is_done(self, update_id: int) -> bool:
        """True, если апдейт уже успешно обработан."""
        ...

    async def mark_done(self, update_id: int) -> None: ...

    async def release(self, update_id: int) -> None: ...
