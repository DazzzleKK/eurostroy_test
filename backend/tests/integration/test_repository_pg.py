"""Репозиторий против настоящего PostgreSQL.

Тест включается переменной ``TEST_DATABASE_URL``: без неё он пропускается,
чтобы обычный прогон не требовал контейнера.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from eurostroy.domain.product import JPEG, Product, ProductImage
from eurostroy.infrastructure.db.models import Base
from eurostroy.infrastructure.db.repository import SqlProductRepository

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="TEST_DATABASE_URL is not set",
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    assert DATABASE_URL is not None
    engine = create_async_engine(DATABASE_URL, poolclass=None)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db_session:
        yield db_session

    await engine.dispose()


def make_product(title: str, created_at: datetime) -> Product:
    product_id = uuid4()
    return Product(
        id=product_id,
        title=title,
        image=ProductImage(
            object_key=f"products/{product_id}.jpg",
            content_type=JPEG,
            size_bytes=128,
        ),
        created_at=created_at,
    )


async def test_orders_by_created_at_desc(session: AsyncSession) -> None:
    repository = SqlProductRepository(session)
    base = datetime(2024, 10, 15, 12, 0, tzinfo=UTC)

    await repository.add(make_product("старый", base))
    await repository.add(make_product("новый", base + timedelta(minutes=5)))
    await session.commit()

    rows = await repository.list_page(limit=10, before=None)

    assert [row.title for row in rows] == ["новый", "старый"]


async def test_keyset_cursor_does_not_skip_or_repeat(session: AsyncSession) -> None:
    repository = SqlProductRepository(session)
    base = datetime(2024, 10, 15, 12, 0, tzinfo=UTC)
    for index in range(5):
        await repository.add(make_product(f"товар {index}", base + timedelta(minutes=index)))
    await session.commit()

    first = await repository.list_page(limit=2, before=None)
    last = first[-1]
    second = await repository.list_page(limit=2, before=(last.created_at, last.id))

    titles = [row.title for row in first + second]
    assert titles == ["товар 4", "товар 3", "товар 2", "товар 1"]


async def test_get_returns_none_for_unknown_id(session: AsyncSession) -> None:
    repository = SqlProductRepository(session)

    assert await repository.get(uuid4()) is None
