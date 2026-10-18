"""Клавиатуры бота."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from eurostroy.infrastructure.telegram.texts import CREATE_PRODUCT, OPEN_CATALOG

CREATE_PRODUCT_CALLBACK = "catalog:create"


def catalog_keyboard(webapp_url: str, *, is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=OPEN_CATALOG,
                web_app=WebAppInfo(url=webapp_url),
            )
        ]
    ]
    if is_admin:
        rows.append(
            [
                InlineKeyboardButton(
                    text=CREATE_PRODUCT,
                    callback_data=CREATE_PRODUCT_CALLBACK,
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)
