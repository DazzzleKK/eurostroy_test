"""Курсор пагинации: пара (created_at, id) в base64url.

Курсор не подписан: он не даёт доступа к данным, только указывает позицию.
Подделанный курсор приводит к пустой странице, а не к утечке.
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime
from uuid import UUID

from eurostroy.domain.errors import ValidationFailed

_SEPARATOR = "|"


def encode_cursor(created_at: datetime, product_id: UUID) -> str:
    raw = f"{created_at.isoformat()}{_SEPARATOR}{product_id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationFailed("Некорректный курсор") from exc

    created_at_raw, separator, product_id_raw = raw.partition(_SEPARATOR)
    if not separator:
        raise ValidationFailed("Некорректный курсор")

    try:
        return datetime.fromisoformat(created_at_raw), UUID(product_id_raw)
    except ValueError as exc:
        raise ValidationFailed("Некорректный курсор") from exc
