"""Создание товара: проверка картинки, запись в S3, запись в базу."""

from __future__ import annotations

from eurostroy.domain.ports import Clock, IdFactory, ImageStorage, ProductRepository
from eurostroy.domain.product import Product, ProductImage, build_object_key, ensure_image


class CreateProductUseCase:
    def __init__(
        self,
        products: ProductRepository,
        storage: ImageStorage,
        clock: Clock,
        ids: IdFactory,
    ) -> None:
        self._products = products
        self._storage = storage
        self._clock = clock
        self._ids = ids

    async def execute(self, *, title: str, image_bytes: bytes) -> Product:
        """Создаёт товар.

        Порядок важен: сначала объект в S3, потом строка в базе. Если база
        упадёт, останется сиротский объект, который не виден в каталоге.
        Обратный порядок дал бы товар без картинки.
        """
        content_type = ensure_image(image_bytes)
        product_id = self._ids.new_product_id()
        product = Product.create(
            id=product_id,
            title=title,
            image=ProductImage(
                object_key=build_object_key(product_id, content_type),
                content_type=content_type,
                size_bytes=len(image_bytes),
            ),
            created_at=self._clock.now(),
        )

        await self._storage.put(product.image.object_key, image_bytes, content_type)
        await self._products.add(product)
        return product
