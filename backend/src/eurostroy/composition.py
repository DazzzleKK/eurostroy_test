"""Composition root: единственное место, где слои склеиваются.

Всё остальное получает готовые объекты: API через зависимость, бот через
``workflow_data``. Здесь же решается, сколько живёт сессия базы: одна
единица работы на один вызов usecase.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from eurostroy.application.products.create_product import CreateProductUseCase
from eurostroy.application.products.list_products import ListProductsUseCase
from eurostroy.application.products.read_image import ReadProductImageUseCase
from eurostroy.config import Settings
from eurostroy.infrastructure.clock import UtcClock, Uuid4Factory
from eurostroy.infrastructure.db.repository import SqlProductRepository
from eurostroy.infrastructure.db.session import create_engine, create_session_factory
from eurostroy.infrastructure.db.updates import SqlUpdateDeduplicator
from eurostroy.infrastructure.storage.minio_storage import MinioImageStorage

if TYPE_CHECKING:
    from aiogram import Bot, Dispatcher


@dataclass(frozen=True, slots=True)
class HealthReport:
    db: bool
    storage: bool

    @property
    def ok(self) -> bool:
        return self.db and self.storage


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine: AsyncEngine = create_engine(settings)
        self.session_factory: async_sessionmaker[AsyncSession] = create_session_factory(self.engine)
        self.storage = MinioImageStorage.from_settings(settings)
        self.clock = UtcClock()
        self.ids = Uuid4Factory()
        self.deduplicator = SqlUpdateDeduplicator(self.session_factory, self.clock)
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None

        if settings.bot_enabled:
            # Импорт внутри ветки: без токена бот и aiogram-диспетчер не нужны,
            # а при импорте модуля это создало бы цикл composition → bot → handlers.
            from eurostroy.infrastructure.telegram.bot import build_bot_and_dispatcher

            self.bot, self.dispatcher = build_bot_and_dispatcher(
                self.deduplicator,
                self.product_commands,
                settings,
            )

    @asynccontextmanager
    async def product_commands(self) -> AsyncIterator[CreateProductUseCase]:
        """Запись: сессия и транзакция живут ровно один вызов usecase."""
        async with self.session_factory() as session, session.begin():
            yield CreateProductUseCase(
                products=SqlProductRepository(session),
                storage=self.storage,
                clock=self.clock,
                ids=self.ids,
            )

    @asynccontextmanager
    async def catalog(self) -> AsyncIterator[ListProductsUseCase]:
        async with self.session_factory() as session:
            yield ListProductsUseCase(SqlProductRepository(session))

    @asynccontextmanager
    async def product_images(self) -> AsyncIterator[ReadProductImageUseCase]:
        async with self.session_factory() as session:
            yield ReadProductImageUseCase(SqlProductRepository(session), self.storage)

    async def health(self) -> HealthReport:
        db_ok = True
        try:
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        storage_ok = await self.storage.ping()
        return HealthReport(db=db_ok, storage=storage_ok)

    async def dispose(self) -> None:
        if self.bot is not None:
            await self.bot.session.close()
        await self.engine.dispose()
