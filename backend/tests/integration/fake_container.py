"""Тестовый контейнер: подменяет зависимости без PostgreSQL и MinIO."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from eurostroy.application.products.create_product import CreateProductUseCase
from eurostroy.application.products.list_products import ListProductsUseCase
from eurostroy.application.products.read_image import ReadProductImageUseCase
from eurostroy.composition import HealthReport
from eurostroy.config import Settings
from tests.fakes import (
    FixedClock,
    InMemoryImageStorage,
    InMemoryProductRepository,
    SequentialIdFactory,
)

WEBHOOK_SECRET = "test-secret"


class FakeContainer:
    def __init__(self) -> None:
        self.settings = Settings(bot_token="", bot_webhook_secret=WEBHOOK_SECRET)
        self.repository = InMemoryProductRepository()
        self.storage = InMemoryImageStorage()
        self.clock = FixedClock()
        self.ids = SequentialIdFactory()
        self.bot: Any = None
        self.dispatcher: Any = None

    @asynccontextmanager
    async def product_commands(self) -> AsyncIterator[CreateProductUseCase]:
        yield CreateProductUseCase(
            products=self.repository,
            storage=self.storage,
            clock=self.clock,
            ids=self.ids,
        )

    @asynccontextmanager
    async def catalog(self) -> AsyncIterator[ListProductsUseCase]:
        yield ListProductsUseCase(self.repository)

    @asynccontextmanager
    async def product_images(self) -> AsyncIterator[ReadProductImageUseCase]:
        yield ReadProductImageUseCase(self.repository, self.storage)

    async def health(self) -> HealthReport:
        return HealthReport(db=True, storage=True)
