"""Идемпотентность вебхука Telegram.

Telegram повторяет доставку, если не получил быстрый 2xx. Поэтому один
и тот же ``update_id`` может прийти многократно и на разные инстансы.
Статус живёт в PostgreSQL: ``processing`` (в работе), ``done`` (обработан).
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import and_, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eurostroy.domain.ports import Clock
from eurostroy.infrastructure.db.models import TelegramUpdateRow

STALE_AFTER = timedelta(minutes=5)


class SqlUpdateDeduplicator:
    """Атомарный захват апдейта.

    Новая строка вставляется, повторная с истёкшим ``processing``
    перезаписывается, а свежая или завершённая отбрасывается. Всё это
    один ``INSERT ... ON CONFLICT``, поэтому гонки нет и блокировки
    между инстансами не нужны.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        clock: Clock,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    async def claim(self, update_id: int) -> bool:
        now = self._clock.now()
        cutoff = now - STALE_AFTER
        statement = (
            pg_insert(TelegramUpdateRow)
            .values(update_id=update_id, status="processing", received_at=now)
            .on_conflict_do_update(
                index_elements=[TelegramUpdateRow.update_id],
                set_={"status": "processing", "received_at": now},
                where=and_(
                    TelegramUpdateRow.status != "done",
                    TelegramUpdateRow.received_at < cutoff,
                ),
            )
            .returning(TelegramUpdateRow.update_id)
        )

        async with self._session_factory() as session, session.begin():
            result = await session.execute(statement)
            return result.scalar_one_or_none() is not None

    async def mark_done(self, update_id: int) -> None:
        statement = (
            update(TelegramUpdateRow)
            .where(TelegramUpdateRow.update_id == update_id)
            .values(status="done", processed_at=self._clock.now())
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def is_done(self, update_id: int) -> bool:
        statement = select(TelegramUpdateRow.status).where(TelegramUpdateRow.update_id == update_id)
        async with self._session_factory() as session:
            status = await session.scalar(statement)
        return status == "done"

    async def release(self, update_id: int) -> None:
        statement = delete(TelegramUpdateRow).where(TelegramUpdateRow.update_id == update_id)
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)
