from __future__ import annotations

from eurostroy.infrastructure.telegram import texts
from eurostroy.infrastructure.telegram.keyboards import (
    CREATE_PRODUCT_CALLBACK,
    catalog_keyboard,
)


def test_greeting_mentions_product_and_catalog() -> None:
    greeting = texts.greeting(is_admin=False)

    assert texts.GREETING_TITLE in greeting
    assert texts.GREETING_BODY in greeting
    assert texts.ADMIN_HINT not in greeting


def test_greeting_hints_admin_about_photo() -> None:
    assert texts.ADMIN_HINT in texts.greeting(is_admin=True)


def test_created_message_contains_title() -> None:
    assert texts.PRODUCT_CREATED.format(title="Смартфон") == "Товар добавлен: Смартфон"


def test_user_keyboard_has_only_catalog_button() -> None:
    keyboard = catalog_keyboard("https://example.com", is_admin=False)

    assert len(keyboard.inline_keyboard) == 1
    button = keyboard.inline_keyboard[0][0]
    assert button.text == texts.OPEN_CATALOG
    assert button.web_app is not None
    assert button.web_app.url == "https://example.com"


def test_admin_keyboard_adds_create_button() -> None:
    keyboard = catalog_keyboard("https://example.com", is_admin=True)

    assert len(keyboard.inline_keyboard) == 2
    create_button = keyboard.inline_keyboard[1][0]
    assert create_button.text == texts.CREATE_PRODUCT
    assert create_button.callback_data == CREATE_PRODUCT_CALLBACK
