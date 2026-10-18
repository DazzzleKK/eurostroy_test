"""Хендлеры бота.

Состояния диалога не хранятся: фото с подписью от админа принимается в любой
момент. Кнопка «Создать товар» только подсказывает формат сообщения, поэтому
бот остаётся stateless и запускается в нескольких инстансах.
"""

from __future__ import annotations

import io
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from eurostroy.application.products.factory import ProductCommandsFactory
from eurostroy.config import Settings
from eurostroy.domain.errors import DomainError
from eurostroy.infrastructure.telegram import texts
from eurostroy.infrastructure.telegram.keyboards import (
    CREATE_PRODUCT_CALLBACK,
    catalog_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="catalog")


def is_admin(user_id: int | None, admins: frozenset[int]) -> bool:
    return user_id is not None and user_id in admins


def user_id_of(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


async def send_greeting(message: Message, settings: Settings) -> None:
    admin = is_admin(user_id_of(message), settings.admins)
    await message.answer(
        texts.greeting(is_admin=admin),
        reply_markup=catalog_keyboard(settings.webapp_url, is_admin=admin),
    )


@router.message(CommandStart())
async def on_start(message: Message, settings: Settings) -> None:
    await send_greeting(message, settings)


@router.message(Command("new"))
async def on_new_command(message: Message, settings: Settings) -> None:
    if not is_admin(user_id_of(message), settings.admins):
        await message.answer(texts.ONLY_ADMIN)
        return
    await message.answer(
        texts.NEED_PHOTO,
        reply_markup=catalog_keyboard(settings.webapp_url, is_admin=True),
    )


@router.callback_query(F.data == CREATE_PRODUCT_CALLBACK)
async def on_create_product_button(callback: CallbackQuery, settings: Settings) -> None:
    await callback.answer()

    target = callback.message
    if not isinstance(target, Message):
        # Старое сообщение, которое бот уже не может редактировать.
        return

    if not is_admin(callback.from_user.id, settings.admins):
        await target.answer(texts.ONLY_ADMIN)
        return

    await target.answer(texts.NEED_PHOTO)


@router.message(F.photo)
async def on_photo(
    message: Message,
    settings: Settings,
    product_commands: ProductCommandsFactory,
) -> None:
    user_id = user_id_of(message)
    if not is_admin(user_id, settings.admins):
        await message.answer(texts.ONLY_ADMIN)
        return

    title = (message.caption or "").strip()
    if not title or not message.photo or message.bot is None:
        await message.answer(texts.NEED_PHOTO)
        return

    buffer = io.BytesIO()
    await message.bot.download(message.photo[-1], buffer)

    try:
        async with product_commands() as use_case:
            product = await use_case.execute(title=title, image_bytes=buffer.getvalue())
    except DomainError as error:
        await message.answer(error.message)
        return
    except Exception:
        logger.exception(
            "product creation failed",
            extra={"telegram_message_id": message.message_id, "user_id": user_id},
        )
        await message.answer(texts.CREATE_FAILED)
        return

    await message.answer(texts.PRODUCT_CREATED.format(title=product.title))


@router.message(F.text)
async def on_text(message: Message, settings: Settings) -> None:
    await send_greeting(message, settings)
