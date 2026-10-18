"""Служебные команды: бакет, вебхук, ожидание зависимостей.

Отдельный CLI, а не код в ``on_startup``: при нескольких инстансах
``set_webhook`` и миграции выполнялись бы каждым из них одновременно.
"""

from __future__ import annotations

import argparse
import asyncio
import time

from aiogram import Bot
from sqlalchemy import text

from eurostroy.config import Settings, get_settings
from eurostroy.infrastructure.db.session import create_engine
from eurostroy.infrastructure.storage.minio_storage import MinioImageStorage

READY_TIMEOUT_SECONDS = 90.0


async def wait_deps(settings: Settings) -> None:
    """Ждёт PostgreSQL и MinIO: init-джоба не должна падать от гонки старта."""
    engine = create_engine(settings)
    storage = MinioImageStorage.from_settings(settings)
    db_ready = False
    s3_ready = False
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS

    try:
        while time.monotonic() < deadline:
            if not db_ready:
                try:
                    async with engine.connect() as connection:
                        await connection.execute(text("SELECT 1"))
                    db_ready = True
                except Exception:
                    db_ready = False

            if not s3_ready:
                s3_ready = await storage.ping_server()

            if db_ready and s3_ready:
                print("dependencies are ready")
                return

            await asyncio.sleep(1.0)
    finally:
        await engine.dispose()

    raise SystemExit("dependencies are not ready in time")


async def ensure_bucket(settings: Settings) -> None:
    storage = MinioImageStorage.from_settings(settings)
    await storage.ensure_bucket()
    print(f"bucket ready: {settings.s3_bucket}")


async def set_webhook(settings: Settings) -> None:
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set")
    if not settings.bot_webhook_secret:
        raise SystemExit("BOT_WEBHOOK_SECRET is not set")

    async with Bot(token=settings.bot_token) as bot:
        await bot.set_webhook(
            url=settings.webhook_url,
            secret_token=settings.bot_webhook_secret,
            allowed_updates=["message"],
            drop_pending_updates=False,
        )
    print(f"webhook set: {settings.webhook_url}")


async def delete_webhook(settings: Settings) -> None:
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set")

    async with Bot(token=settings.bot_token) as bot:
        await bot.delete_webhook(drop_pending_updates=False)
    print("webhook deleted")


async def webhook_info(settings: Settings) -> None:
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN is not set")

    async with Bot(token=settings.bot_token) as bot:
        info = await bot.get_webhook_info()
    print(f"url: {info.url}")
    print(f"pending_updates: {info.pending_update_count}")
    print(f"last_error: {info.last_error_message}")


COMMANDS = {
    "wait-deps": wait_deps,
    "ensure-bucket": ensure_bucket,
    "set-webhook": set_webhook,
    "delete-webhook": delete_webhook,
    "webhook-info": webhook_info,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eurostroy")
    parser.add_argument("command", choices=sorted(COMMANDS))
    args = parser.parse_args(argv)

    settings = get_settings()
    asyncio.run(COMMANDS[args.command](settings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
