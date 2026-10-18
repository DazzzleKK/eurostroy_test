"""Доменные ошибки.

Каждая ошибка несёт машинный ``code``: по нему транспорт строит HTTP-ответ,
а бот выбирает текст для пользователя. Тексты сообщений русские, потому что
их видит конечный пользователь в Telegram.
"""

from __future__ import annotations


class DomainError(Exception):
    """Базовая ошибка домена. Наружу отдаётся только ``code`` и сообщение."""

    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationFailed(DomainError):
    code = "validation_failed"


class UnsupportedImage(DomainError):
    code = "unsupported_image"


class ImageTooLarge(DomainError):
    code = "image_too_large"


class ProductNotFound(DomainError):
    code = "product_not_found"
