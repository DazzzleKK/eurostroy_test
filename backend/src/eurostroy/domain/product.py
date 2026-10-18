"""Сущность товара и правила, которым она подчиняется.

Тип изображения определяется по сигнатуре файла, а не по тому, что прислали
в заголовке: Telegram отдаёт фото как JPEG, но проверка не должна полагаться
на внешнее утверждение.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from eurostroy.domain.errors import ImageTooLarge, UnsupportedImage, ValidationFailed

MAX_TITLE_LENGTH = 200
MAX_IMAGE_BYTES = 10 * 1024 * 1024

JPEG = "image/jpeg"
PNG = "image/png"
WEBP = "image/webp"

ALLOWED_CONTENT_TYPES = frozenset({JPEG, PNG, WEBP})

EXTENSIONS: dict[str, str] = {JPEG: ".jpg", PNG: ".png", WEBP: ".webp"}

_WHITESPACE = re.compile(r"\s+")
_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True, slots=True)
class ProductImage:
    """Ссылка на объект в S3 и его метаданные."""

    object_key: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class Product:
    id: UUID
    title: str
    image: ProductImage
    created_at: datetime

    @staticmethod
    def create(
        *,
        id: UUID,
        title: str,
        image: ProductImage,
        created_at: datetime,
    ) -> Product:
        return Product(
            id=id,
            title=normalize_title(title),
            image=image,
            created_at=created_at,
        )


def normalize_title(raw: str) -> str:
    """Обрезает пробелы по краям и схлопывает внутренние."""
    cleaned = _WHITESPACE.sub(" ", raw.strip())
    if not cleaned:
        raise ValidationFailed("Название товара не может быть пустым")
    if len(cleaned) > MAX_TITLE_LENGTH:
        raise ValidationFailed(f"Название длиннее {MAX_TITLE_LENGTH} символов")
    return cleaned


def detect_image_content_type(data: bytes) -> str | None:
    """Возвращает MIME-тип по сигнатуре или ``None``, если это не картинка."""
    if data.startswith(_JPEG_MAGIC):
        return JPEG
    if data.startswith(_PNG_MAGIC):
        return PNG
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return WEBP
    return None


def ensure_image(data: bytes) -> str:
    """Проверяет размер и тип, возвращает определённый MIME-тип."""
    if len(data) > MAX_IMAGE_BYTES:
        limit_mb = MAX_IMAGE_BYTES // (1024 * 1024)
        raise ImageTooLarge(f"Файл больше {limit_mb} МБ")
    content_type = detect_image_content_type(data)
    if content_type is None or content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedImage("Поддерживаются JPEG, PNG и WebP")
    return content_type


def build_object_key(product_id: UUID, content_type: str) -> str:
    return f"products/{product_id}{EXTENSIONS[content_type]}"
