"""Сборка aiogram-бота и диспетчера."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from eurostroy.application.products.factory import ProductCommandsFactory
from eurostroy.config import Settings
from eurostroy.domain.ports import UpdateDeduplicator
from eurostroy.infrastructure.telegram.handlers import router as catalog_router
from eurostroy.infrastructure.telegram.middleware import DedupeMiddleware


def build_bot_and_dispatcher(
    deduplicator: UpdateDeduplicator,
    product_commands: ProductCommandsFactory,
    settings: Settings,
) -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(DedupeMiddleware(deduplicator))
    dispatcher.include_router(catalog_router)
    dispatcher["settings"] = settings
    dispatcher["product_commands"] = product_commands
    return bot, dispatcher
