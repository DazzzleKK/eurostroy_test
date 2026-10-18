"""Точка входа uvicorn: ``uvicorn eurostroy.main:app``."""

from __future__ import annotations

from eurostroy.api.app import create_app

app = create_app()
