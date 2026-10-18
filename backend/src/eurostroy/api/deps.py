"""Зависимости FastAPI."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from eurostroy.composition import Container


def get_container(request: Request) -> Container:
    container = getattr(request.app.state, "container", None)
    if not isinstance(container, Container):
        raise RuntimeError("container is not initialized")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]
