"""DTO прикладного слоя.

Это не Pydantic-схемы: транспорт сам решает, как сериализовать. Здесь только
данные, которые нужны presentation-слою.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from eurostroy.domain.product import Product


@dataclass(frozen=True, slots=True)
class ProductView:
    id: UUID
    title: str
    image_url: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProductPage:
    items: list[ProductView]
    next_cursor: str | None


def image_url(product_id: UUID) -> str:
    """Относительный путь: страница и картинки живут на одном origin."""
    return f"/api/products/{product_id}/image"


def to_view(product: Product) -> ProductView:
    return ProductView(
        id=product.id,
        title=product.title,
        image_url=image_url(product.id),
        created_at=product.created_at,
    )
