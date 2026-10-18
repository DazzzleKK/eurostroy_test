from __future__ import annotations

import pytest

from eurostroy.domain.errors import ImageTooLarge, UnsupportedImage, ValidationFailed
from eurostroy.domain.product import (
    JPEG,
    MAX_IMAGE_BYTES,
    MAX_TITLE_LENGTH,
    PNG,
    WEBP,
    detect_image_content_type,
    ensure_image,
    normalize_title,
)
from tests.fakes import JPEG_BYTES, PNG_BYTES, TEXT_BYTES, WEBP_BYTES


def test_normalize_title_collapses_whitespace() -> None:
    assert normalize_title("  Смартфон   Xiaomi \n 14  ") == "Смартфон Xiaomi 14"


def test_normalize_title_rejects_blank() -> None:
    with pytest.raises(ValidationFailed):
        normalize_title("   \t\n ")


def test_normalize_title_rejects_long_value() -> None:
    with pytest.raises(ValidationFailed):
        normalize_title("x" * (MAX_TITLE_LENGTH + 1))


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (JPEG_BYTES, JPEG),
        (PNG_BYTES, PNG),
        (WEBP_BYTES, WEBP),
        (TEXT_BYTES, None),
        (b"", None),
    ],
)
def test_detect_image_content_type_by_signature(data: bytes, expected: str | None) -> None:
    assert detect_image_content_type(data) == expected


def test_ensure_image_returns_detected_type() -> None:
    assert ensure_image(PNG_BYTES) == PNG


def test_ensure_image_rejects_text() -> None:
    with pytest.raises(UnsupportedImage):
        ensure_image(TEXT_BYTES)


def test_ensure_image_rejects_oversized_payload() -> None:
    oversized = JPEG_BYTES + b"\x00" * MAX_IMAGE_BYTES
    with pytest.raises(ImageTooLarge):
        ensure_image(oversized)
