"""Листинг каталога с keyset-пагинацией."""

from __future__ import annotations

from eurostroy.application.products.cursor import decode_cursor, encode_cursor
from eurostroy.application.products.dto import ProductPage, to_view
from eurostroy.domain.errors import ValidationFailed
from eurostroy.domain.ports import ProductRepository

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class ListProductsUseCase:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(
        self,
        *,
        limit: int = DEFAULT_PAGE_SIZE,
        cursor: str | None = None,
    ) -> ProductPage:
        if limit < 1:
            raise ValidationFailed("limit должен быть положительным")
        limit = min(limit, MAX_PAGE_SIZE)

        before = decode_cursor(cursor) if cursor else None
        # Запрашиваем на одну строку больше, чтобы понять, есть ли следующая страница.
        rows = await self._products.list_page(limit=limit + 1, before=before)

        has_next = len(rows) > limit
        items = rows[:limit]
        next_cursor = None
        if has_next and items:
            last = items[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        return ProductPage(items=[to_view(product) for product in items], next_cursor=next_cursor)
