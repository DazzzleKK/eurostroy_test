"""Общие тестовые двойники: без базы, S3 и Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from eurostroy.domain.product import Product

JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 64
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
WEBP_BYTES = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"\x00" * 64
TEXT_BYTES = b"not an image at all"


class InMemoryProductRepository:
    def __init__(self) -> None:
        self.rows: list[Product] = []
        self.list_calls: list[tuple[int, tuple[datetime, UUID] | None]] = []

    async def add(self, product: Product) -> None:
        self.rows.append(product)

    async def get(self, product_id: UUID) -> Product | None:
        return next((row for row in self.rows if row.id == product_id), None)

    async def list_page(
        self,
        *,
        limit: int,
        before: tuple[datetime, UUID] | None,
    ) -> list[Product]:
        self.list_calls.append((limit, before))
        ordered = sorted(self.rows, key=lambda row: (row.created_at, row.id), reverse=True)
        if before is not None:
            ordered = [row for row in ordered if (row.created_at, row.id) < before]
        return ordered[:limit]


class InMemoryImageStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = (data, content_type)

    async def get(self, key: str) -> bytes | None:
        stored = self.objects.get(key)
        return stored[0] if stored else None


class FixedClock:
    def __init__(self, moment: datetime | None = None) -> None:
        self.moment = moment or datetime(2024, 10, 15, 11, 20, tzinfo=UTC)

    def now(self) -> datetime:
        return self.moment


class SequentialIdFactory:
    def __init__(self) -> None:
        self._counter = 0

    def new_product_id(self) -> UUID:
        self._counter += 1
        return UUID(int=self._counter)
