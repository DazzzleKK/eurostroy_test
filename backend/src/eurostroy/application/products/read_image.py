"""Чтение изображения товара для отдачи через API."""

from __future__ import annotations

from uuid import UUID

from eurostroy.domain.errors import ProductNotFound
from eurostroy.domain.ports import ImageStorage, ProductRepository


class ReadProductImageUseCase:
    def __init__(self, products: ProductRepository, storage: ImageStorage) -> None:
        self._products = products
        self._storage = storage

    async def execute(self, product_id: UUID) -> tuple[bytes, str]:
        product = await self._products.get(product_id)
        if product is None:
            raise ProductNotFound("Товар не найден")

        data = await self._storage.get(product.image.object_key)
        if data is None:
            # Строка в базе есть, а объекта в S3 нет: для клиента это тот же
            # «не найден», но в логах останется reason.
            raise ProductNotFound("Изображение недоступно")

        return data, product.image.content_type
