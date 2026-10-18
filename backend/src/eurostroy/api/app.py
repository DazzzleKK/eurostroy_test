"""Сборка FastAPI-приложения."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from eurostroy.api.errors import domain_error_handler
from eurostroy.api.routers import health, products, telegram
from eurostroy.composition import Container
from eurostroy.config import Settings, get_settings
from eurostroy.domain.errors import DomainError


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        container = Container(resolved)
        application.state.container = container
        try:
            yield
        finally:
            await container.dispose()

    application = FastAPI(
        title="Eurostroy Catalog",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_exception_handler(DomainError, domain_error_handler)
    application.include_router(products.router)
    application.include_router(health.router)
    application.include_router(telegram.router)
    return application
