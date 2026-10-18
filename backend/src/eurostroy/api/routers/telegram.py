"""Вебхук Telegram."""

from __future__ import annotations

import hmac
import logging

from aiogram.types import Update
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError

from eurostroy.api.deps import ContainerDep
from eurostroy.infrastructure.telegram.middleware import UpdateIsBusy

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"


@router.post("/webhook")
async def telegram_webhook(request: Request, container: ContainerDep) -> dict[str, bool]:
    settings = container.settings
    expected = settings.bot_webhook_secret
    supplied = request.headers.get(SECRET_HEADER, "")

    if not expected or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid secret token")

    if container.bot is None or container.dispatcher is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="bot is not configured",
        )

    try:
        payload = await request.json()
    except ValueError:
        logger.warning("update with invalid json dropped")
        return {"ok": True}

    try:
        update = Update.model_validate(payload)
    except ValidationError:
        # Битый апдейт не станет валидным при повторе, поэтому отвечаем 200,
        # чтобы Telegram не зациклился на нём.
        logger.warning("malformed update dropped", extra={"payload": payload})
        return {"ok": True}

    try:
        await container.dispatcher.feed_update(container.bot, update)
    except UpdateIsBusy as exc:
        # Тот же апдейт уже в работе на другом инстансе. Пусть Telegram
        # повторит позже: отвечать 200 нельзя, иначе при падении обработчика
        # апдейт потеряется.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="update is being processed",
            headers={"Retry-After": "1"},
        ) from exc

    return {"ok": True}
