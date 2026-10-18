"""Контракт между ботом и прикладным слоем.

Транспорту не нужен весь контейнер: хендлеру достаточно функции, которая
открывает единицу работы. Так инфраструктура не знает composition root.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from eurostroy.application.products.create_product import CreateProductUseCase

type ProductCommandsFactory = Callable[[], AbstractAsyncContextManager[CreateProductUseCase]]
