"""Pydantic-схемы HTTP-ответов."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: UUID
    title: str
    image_url: str
    created_at: datetime


class ProductListOut(BaseModel):
    items: list[ProductOut]
    next_cursor: str | None


class HealthOut(BaseModel):
    status: str
    db: bool
    storage: bool


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorOut(BaseModel):
    error: ErrorBody
