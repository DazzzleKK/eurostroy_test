"""Репозиторий товаров на SQLAlchemy."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from eurostroy.domain.product import Product, ProductImage
from eurostroy.infrastructure.db.models import ProductRow


class SqlProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, product: Product) -> None:
        self._session.add(
            ProductRow(
                id=product.id,
                title=product.title,
                image_key=product.image.object_key,
                content_type=product.image.content_type,
                size_bytes=product.image.size_bytes,
                created_at=product.created_at,
            )
        )
        await self._session.flush()

    async def get(self, product_id: UUID) -> Product | None:
        row = await self._session.get(ProductRow, product_id)
        return _to_domain(row) if row is not None else None

    async def list_page(
        self,
        *,
        limit: int,
        before: tuple[datetime, UUID] | None,
    ) -> list[Product]:
        stmt = (
            select(ProductRow)
            .order_by(ProductRow.created_at.desc(), ProductRow.id.desc())
            .limit(limit)
        )
        if before is not None:
            moment, product_id = before
            # Сравнение кортежей записано явно: так плагин запросов и индекс
            # понимают одно и то же условие.
            stmt = stmt.where(
                or_(
                    ProductRow.created_at < moment,
                    and_(ProductRow.created_at == moment, ProductRow.id < product_id),
                )
            )

        result = await self._session.execute(stmt)
        return [_to_domain(row) for row in result.scalars().all()]


def _to_domain(row: ProductRow) -> Product:
    return Product(
        id=row.id,
        title=row.title,
        image=ProductImage(
            object_key=row.image_key,
            content_type=row.content_type,
            size_bytes=row.size_bytes,
        ),
        created_at=row.created_at,
    )
