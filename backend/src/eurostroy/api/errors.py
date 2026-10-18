"""Обработчики доменных ошибок.

Формат один на всё API: ``{"error": {"code", "message"}}``. Внутренние
исключения наружу не отдаются, только код и короткий текст.
"""

from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import JSONResponse

from eurostroy.domain.errors import DomainError

_STATUS_BY_CODE: dict[str, int] = {
    "validation_failed": status.HTTP_400_BAD_REQUEST,
    "unsupported_image": status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    "image_too_large": status.HTTP_413_CONTENT_TOO_LARGE,
    "product_not_found": status.HTTP_404_NOT_FOUND,
}


def _as_domain_error(exc: Exception) -> DomainError:
    return exc if isinstance(exc, DomainError) else DomainError(str(exc))


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    error = _as_domain_error(exc)
    status_code = _STATUS_BY_CODE.get(error.code, status.HTTP_400_BAD_REQUEST)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": error.code, "message": error.message}},
    )
