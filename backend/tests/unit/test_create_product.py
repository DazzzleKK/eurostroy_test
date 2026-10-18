from __future__ import annotations

import pytest

from eurostroy.application.products.create_product import CreateProductUseCase
from eurostroy.domain.errors import ImageTooLarge, UnsupportedImage, ValidationFailed
from eurostroy.domain.product import PNG, Product
from tests.fakes import (
    JPEG_BYTES,
    PNG_BYTES,
    TEXT_BYTES,
    FixedClock,
    InMemoryImageStorage,
    InMemoryProductRepository,
    SequentialIdFactory,
)


def build_use_case() -> tuple[
    CreateProductUseCase, InMemoryProductRepository, InMemoryImageStorage
]:
    repository = InMemoryProductRepository()
    storage = InMemoryImageStorage()
    use_case = CreateProductUseCase(
        products=repository,
        storage=storage,
        clock=FixedClock(),
        ids=SequentialIdFactory(),
    )
    return use_case, repository, storage


async def test_creates_product_and_uploads_image() -> None:
    use_case, repository, storage = build_use_case()

    product = await use_case.execute(title="  Смартфон   Xiaomi ", image_bytes=PNG_BYTES)

    assert product.title == "Смартфон Xiaomi"
    assert product.image.content_type == PNG
    assert product.image.size_bytes == len(PNG_BYTES)
    assert product.image.object_key == f"products/{product.id}.png"
    assert storage.objects[product.image.object_key] == (PNG_BYTES, PNG)
    assert repository.rows == [product]


async def test_rejects_non_image_before_touching_storage() -> None:
    use_case, repository, storage = build_use_case()

    with pytest.raises(UnsupportedImage):
        await use_case.execute(title="Товар", image_bytes=TEXT_BYTES)

    assert storage.objects == {}
    assert repository.rows == []


async def test_rejects_oversized_image() -> None:
    use_case, repository, _storage = build_use_case()

    with pytest.raises(ImageTooLarge):
        await use_case.execute(title="Товар", image_bytes=JPEG_BYTES + b"\x00" * (11 * 1024 * 1024))

    assert repository.rows == []


async def test_rejects_empty_title() -> None:
    use_case, _repository, _storage = build_use_case()

    with pytest.raises(ValidationFailed):
        await use_case.execute(title="   ", image_bytes=JPEG_BYTES)


async def test_product_id_is_taken_from_id_factory() -> None:
    use_case, _repository, _storage = build_use_case()

    product: Product = await use_case.execute(title="Товар", image_bytes=JPEG_BYTES)

    assert str(product.id) == "00000000-0000-0000-0000-000000000001"
