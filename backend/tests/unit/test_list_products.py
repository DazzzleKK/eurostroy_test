from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from eurostroy.application.products.create_product import CreateProductUseCase
from eurostroy.application.products.list_products import MAX_PAGE_SIZE, ListProductsUseCase
from eurostroy.domain.errors import ValidationFailed
from tests.fakes import (
    JPEG_BYTES,
    FixedClock,
    InMemoryImageStorage,
    InMemoryProductRepository,
    SequentialIdFactory,
)

START = datetime(2024, 10, 15, 11, 20, tzinfo=UTC)


async def seed(repository: InMemoryProductRepository, count: int) -> None:
    for offset in range(count):
        clock = FixedClock(START + timedelta(minutes=offset))
        use_case = CreateProductUseCase(
            products=repository,
            storage=InMemoryImageStorage(),
            clock=clock,
            ids=SequentialIdFactory(),
        )
        await use_case.execute(title=f"Товар {offset + 1}", image_bytes=JPEG_BYTES)


async def test_returns_first_page_and_next_cursor() -> None:
    repository = InMemoryProductRepository()
    await seed(repository, 5)

    page = await ListProductsUseCase(repository).execute(limit=2)

    assert [item.title for item in page.items] == ["Товар 5", "Товар 4"]
    assert page.next_cursor is not None
    assert repository.list_calls == [(3, None)]


async def test_walks_through_pages_without_gaps() -> None:
    repository = InMemoryProductRepository()
    await seed(repository, 5)
    use_case = ListProductsUseCase(repository)

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(3):
        page = await use_case.execute(limit=2, cursor=cursor)
        seen.extend(item.title for item in page.items)
        cursor = page.next_cursor
        if cursor is None:
            break

    assert seen == ["Товар 5", "Товар 4", "Товар 3", "Товар 2", "Товар 1"]
    assert cursor is None


async def test_last_page_has_no_cursor() -> None:
    repository = InMemoryProductRepository()
    await seed(repository, 2)

    page = await ListProductsUseCase(repository).execute(limit=5)

    assert len(page.items) == 2
    assert page.next_cursor is None


async def test_limit_is_capped() -> None:
    repository = InMemoryProductRepository()

    await ListProductsUseCase(repository).execute(limit=10_000)

    assert repository.list_calls[0][0] == MAX_PAGE_SIZE + 1


async def test_zero_limit_is_rejected() -> None:
    repository = InMemoryProductRepository()

    with pytest.raises(ValidationFailed):
        await ListProductsUseCase(repository).execute(limit=0)


async def test_broken_cursor_is_rejected() -> None:
    repository = InMemoryProductRepository()

    with pytest.raises(ValidationFailed):
        await ListProductsUseCase(repository).execute(limit=2, cursor="not-a-cursor")


async def test_image_url_points_to_backend_route() -> None:
    repository = InMemoryProductRepository()
    await seed(repository, 1)

    page = await ListProductsUseCase(repository).execute(limit=1)

    item = page.items[0]
    assert item.image_url == f"/api/products/{item.id}/image"
