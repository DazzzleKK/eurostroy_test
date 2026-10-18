"""Идемпотентность апдейтов на уровне middleware.

Middleware стоит на уровне ``update``: до роутеров, поэтому дубль
не доходит до хендлеров вообще.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from eurostroy.domain.ports import UpdateDeduplicator

logger = logging.getLogger(__name__)


class UpdateIsBusy(RuntimeError):
    """Апдейт уже обрабатывается другим инстансом.

    Вебхук отвечает 503, чтобы Telegram повторил доставку позже: тихо
    проглотить апдейт нельзя, иначе он потеряется при падении того инстанса.
    """

    def __init__(self, update_id: int) -> None:
        super().__init__(f"update {update_id} is being processed")
        self.update_id = update_id


class DedupeMiddleware(BaseMiddleware):
    def __init__(self, deduplicator: UpdateDeduplicator) -> None:
        self._deduplicator = deduplicator

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Update):
            return await handler(event, data)

        update_id = event.update_id
        if not await self._deduplicator.claim(update_id):
            if await self._deduplicator.is_done(update_id):
                logger.info("duplicate update skipped", extra={"update_id": update_id})
                return None
            raise UpdateIsBusy(update_id)

        try:
            result = await handler(event, data)
        except Exception:
            # Обработчик упал: снимаем захват, чтобы повторная доставка
            # от Telegram могла попробовать снова.
            await self._deduplicator.release(update_id)
            raise

        await self._deduplicator.mark_done(update_id)
        return result
