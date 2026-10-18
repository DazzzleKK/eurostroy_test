"""Каталог: список товаров и изображение."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response

from eurostroy.api.deps import ContainerDep
from eurostroy.api.schemas import ProductListOut, ProductOut
from eurostroy.application.products.list_products import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/api/products", tags=["products"])

CACHE_FOREVER = "public, max-age=31536000, immutable"


@router.get("", response_model=ProductListOut)
async def list_products(
    container: ContainerDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> ProductListOut:
    async with container.catalog() as use_case:
        page = await use_case.execute(limit=limit, cursor=cursor)

    return ProductListOut(
        items=[
            ProductOut(
                id=item.id,
                title=item.title,
                image_url=item.image_url,
                created_at=item.created_at,
            )
            for item in page.items
        ],
        next_cursor=page.next_cursor,
    )


@router.get(
    "/{product_id}/image",
    responses={404: {"description": "Товар или изображение не найдены"}},
)
async def product_image(product_id: UUID, container: ContainerDep) -> Response:
    async with container.product_images() as use_case:
        data, content_type = await use_case.execute(product_id)

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": CACHE_FOREVER},
    )
