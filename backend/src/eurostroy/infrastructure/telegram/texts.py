"""Тексты бота. Вынесены отдельно, чтобы правки не трогали логику."""

from __future__ import annotations

GREETING_TITLE = "У меня есть товар"
GREETING_BODY = "Каталог открывается кнопкой ниже."
OPEN_CATALOG = "Открыть каталог"
CREATE_PRODUCT = "Создать товар"

ADMIN_HINT = "Вы администратор. Чтобы добавить товар, пришлите фото с названием в подписи."
NEED_PHOTO = "Нужно фото с названием в подписи: прикрепите картинку и подпишите её."
ONLY_ADMIN = "Добавлять товары может только администратор."
PRODUCT_CREATED = "Товар добавлен: {title}"
CREATE_FAILED = "Не получилось сохранить товар. Попробуйте позже."
BOT_NOT_CONFIGURED = "Бот не настроен: не задан BOT_TOKEN."


def greeting(*, is_admin: bool) -> str:
    parts = [f"{GREETING_TITLE}.", GREETING_BODY]
    if is_admin:
        parts.append(ADMIN_HINT)
    return "\n\n".join(parts)
