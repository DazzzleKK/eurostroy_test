# Brief: микросервис каталога (тестовое задание Eurostroy)

## Мета

- **Проект / репозиторий:** `eurostroy_test` (новый, чистый каталог, git ещё не инициализирован)
- **Стек:** Next.js 15 (App Router, TypeScript) + FastAPI + aiogram 3 + PostgreSQL 16 + MinIO, интеграция TMA
- **Тип:** фича (новый проект)
- **Класс изменения:** крупное (новый домен, новый слой, новое приложение, внешние сервисы)
- **Триггеры ревью:** новый домен / слой / приложение; внешние сервисы (Telegram, S3); волна заведомо больше 400 строк diff
- **Статус:** подтверждено оператором

## Карта архитектуры проекта

Каталог пустой, слои задаются этим brief.

| Слой | Пути | Содержимое |
|------|------|------------|
| Domain | `backend/src/eurostroy/domain/` | `product.py` (entity, value objects), `errors.py`, `ports.py` (Protocols, Clock, IdFactory) |
| Application | `backend/src/eurostroy/application/` | `products/create_product.py`, `products/list_products.py`, `products/dto.py` |
| Infrastructure | `backend/src/eurostroy/infrastructure/` | `db/` (models, session, repository, updates), `storage/minio_storage.py`, `telegram/` (bot, handlers, keyboards, texts, middleware), `health.py` |
| Presentation | `backend/src/eurostroy/api/`, `frontend/` | FastAPI app, routers, schemas, error handlers; Next.js App Router |
| Composition root | `backend/src/eurostroy/composition.py`, `config.py` | сборка зависимостей, настройки из env |
| CLI | `backend/src/eurostroy/cli.py` | `migrate`, `ensure-bucket`, `set-webhook`, `delete-webhook` |

**Домены:** `catalog` (товары и их изображения), `telegram` (приём апдейтов, идемпотентность) — второй без своей доменной модели, только инфраструктурный слой.

**Правило зависимостей (проверяется import-linter):**

1. `domain` не импортирует ничего из `eurostroy.*` кроме `domain`.
2. `application` не импортирует `infrastructure`, `api`, `composition`.
3. `infrastructure` не импортирует `api`, `composition`.

**DI / wiring:** конструкторы принимают порты; `composition.py` знает про инфраструктуру и отдаёт готовые usecase. FastAPI-зависимости и aiogram `workflow_data` берут объекты из composition, поэтому тесты подменяют порты без БД и S3.

## Цель (зачем)

Нужен минимальный, но production-честный сервис каталога: админ кладёт товар через бота (название + фото в подписи), фото уходит в MinIO, запись в PostgreSQL; каталог показывается страницей Next.js и открывается как Telegram Mini App. Заказчик отдельно проверяет отказоустойчивость: каждый компонент запускается в нескольких инстансах и не держит состояние в памяти.

Поэтому архитектурные решения подчинены stateless-требованию: идемпотентность апдейтов в PostgreSQL, отключённый FSM в боте, отсутствие файлов на локальном диске, миграции и создание бакета отдельными CLI-командами, а не в `on_startup` каждого инстанса.

## Что меняется (что)

- Новый backend: домен каталога, usecases создания и листинга, SQLAlchemy-репозиторий, MinIO-адаптер, FastAPI (каталог, отдача картинок, healthz, Telegram webhook).
- Новый Telegram-бот на aiogram 3 в webhook-режиме: приветствие «У меня есть товар» + кнопка Mini App, приём фото с подписью от админа, идемпотентность по `update_id`.
- Новый frontend на Next.js: страница «Каталог» со списком товаров, работает и в браузере, и в TMA (скрипт `telegram-web-app.js`, `ready()`/`expand()`, тема из клиента).
- Deploy: Dockerfile на backend и frontend, `docker-compose.yml` (postgres, minio, backend, frontend, nginx, init-джоба), `.env.example`, README с запуском, масштабированием и настройкой webhook.
- Проверки: ruff, mypy, import-linter, pytest; `next build`; smoke-прогон compose.

## Доменные артефакты (файл vs пакет)

| Домен | Артефакт | Файл / Пакет | Решение |
|-------|----------|--------------|---------|
| catalog | entity `Product`, value objects `ProductImage`, `ProductTitle` | файл `domain/product.py` | простая структура, отдельный пакет не нужен |
| catalog | exceptions | файл `domain/errors.py` | базовый `DomainError` с `code` |
| catalog | ports (`ProductRepository`, `ImageStorage`, `Clock`, `IdFactory`) | файл `domain/ports.py` | `typing.Protocol` |
| catalog | DTO для приложения (`ProductView`, `ProductPage`) | файл `application/products/dto.py` | dataclass, без Pydantic в application |
| telegram | ports (`UpdateDeduplicator`) | файл `domain/ports.py` | Protocol, реализация в infrastructure/db |

Если позже появится второй домен, порты переезжают в пакеты; сейчас файл дешевле.

## Интерфейсы

### `domain/product.py` — Domain

```python
@dataclass(frozen=True, slots=True)
class ProductImage:
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
    def create(*, id: UUID, title: str, image: ProductImage, created_at: datetime) -> "Product": ...


MAX_TITLE_LENGTH = 200
ALLOWED_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAX_IMAGE_BYTES = 10 * 1024 * 1024
```

### `domain/errors.py` — Domain

```python
class DomainError(Exception):
    code: str = "domain_error"


class ValidationFailed(DomainError):
    code = "validation_failed"


class UnsupportedImage(DomainError):
    code = "unsupported_image"


class ImageTooLarge(DomainError):
    code = "image_too_large"


class ProductNotFound(DomainError):
    code = "product_not_found"
```

### `domain/ports.py` — Domain

```python
class ProductRepository(Protocol):
    async def add(self, product: Product) -> None: ...
    async def get(self, product_id: UUID) -> Product | None: ...
    async def list_page(
        self,
        *,
        limit: int,
        before: tuple[datetime, UUID] | None,
    ) -> list[Product]: ...


class ImageStorage(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes | None: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_product_id(self) -> UUID: ...


class UpdateDeduplicator(Protocol):
    async def claim(self, update_id: int) -> bool: ...
    async def mark_done(self, update_id: int) -> None: ...
    async def release(self, update_id: int) -> None: ...
```

### `application/products/dto.py` — Application

```python
@dataclass(frozen=True, slots=True)
class ProductView:
    id: UUID
    title: str
    image_url: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProductPage:
    items: list[ProductView]
    next_cursor: str | None
```

### `application/products/create_product.py` — Application

```python
class CreateProductUseCase:
    def __init__(
        self,
        products: ProductRepository,
        storage: ImageStorage,
        clock: Clock,
        ids: IdFactory,
    ) -> None: ...

    async def execute(self, *, title: str, image_bytes: bytes, content_type: str) -> Product: ...
```

Поведение: нормализует `title` (strip, схлопывание пробелов), валидирует длину и тип картинки по сигнатуре, проверяет размер, кладёт объект в хранилище по ключу `products/{product_id}.{ext}`, сохраняет запись. Если сохранение в БД упало, объект в хранилище остаётся сиротой; удаление сирот в scope не входит.

### `application/products/list_products.py` — Application

```python
class ListProductsUseCase:
    def __init__(self, products: ProductRepository) -> None: ...

    async def execute(self, *, limit: int = 20, cursor: str | None = None) -> ProductPage: ...
```

Курсор: `base64url` от `created_at|id`, keyset-пагинация по `(created_at, id) DESC`. `limit` ограничен 1..100.

### HTTP-контракт — Presentation

| Метод | Путь | Ответ |
|-------|------|-------|
| GET | `/api/products?limit=20&cursor=<str>` | `{"items":[{"id","title","image_url","created_at"}],"next_cursor": str \| null}` |
| GET | `/api/products/{id}/image` | binary, `Content-Type` из записи, `Cache-Control: public, max-age=31536000, immutable` |
| GET | `/api/healthz` | `{"status":"ok","db":true,"storage":true}`, 503 при недоступности зависимости |
| POST | `/api/telegram/webhook` | `{"ok":true}`; запрос проверяется по `X-Telegram-Bot-Api-Secret-Token` |

`image_url` отдаётся относительным (`/api/products/{id}/image`), чтобы страница и картинки жили на одном origin: работает в браузере и в TMA без CORS.

Ошибки: `{"error": {"code": "<code>", "message": "<текст>"}}`, маппинг `DomainError.code` → HTTP 400/404/413/415/422, неизвестное → 500 без деталей.

### Telegram-контракт — Infrastructure (aiogram)

| Событие | Поведение |
|---------|-----------|
| `/start`, любой текст от не-админа | «У меня есть товар», inline-кнопка «Открыть каталог» (`web_app`) |
| `/start`, любой текст от админа | то же + подсказка: «Пришлите фото с названием в подписи» |
| фото с подписью от админа | создание товара, ответ «Товар добавлен: <title>» |
| фото без подписи / подпись без фото от админа | подсказка, что нужно прислать |
| фото от не-админа | отказ без деталей |
| ошибка домена | текст по `code`; прочие ошибки → «Не получилось, попробуйте позже», лог с `update_id` |

Состояния диалога не хранятся: фото с подписью принимается в любой момент от админа. Так бот остаётся stateless без Redis и FSM-хранилища.

## Поведение после изменений

1. `docker compose up` поднимает postgres, minio, backend, frontend, nginx; init-джоба применяет миграции и создаёт бакет; каталог открыт на `http://localhost:8080/`.
2. `docker compose up --scale backend=3 --scale frontend=2` даёт работающий каталог и бота: nginx распределяет запросы, состояние только в Postgres и MinIO.
3. Повторная доставка одного `update_id` (ретрай Telegram) не создаёт второй товар.
4. Внутри Telegram каталог открывается кнопкой Mini App; вне Telegram страница работает как обычный сайт.
5. `make check` прогоняет ruff, mypy, import-linter, pytest, `next build`; `make smoke` проверяет живой compose.

## Вне scope

- Редактирование и удаление товаров, заказы, цены, категории.
- Очередь задач: обработка апдейта идёт inline в webhook-запросе (Telegram ждёт ответ до ~60 с). Для тяжёлых операций нужна очередь, здесь она лишняя.
- Собственная аутентификация админа веб-каталога (каталог публичный, запись только через бота по `ADMIN_IDS`).
- Удаление осиротевших объектов в MinIO, ретеншн и бэкапы.
- Публичный доступ к бакету: картинки идут через backend, политика бакета остаётся закрытой.
- E2E-тесты в браузере, нагрузочное тестирование, метрики Prometheus.
- UI-дизайн: только аккуратная минимальная вёрстка без библиотек компонентов.

## Критерии готовности

- [ ] Волна 1: домен и usecases покрыты unit-тестами, import-linter зелёный, `ruff`/`mypy` без ошибок.
- [ ] Волна 2: миграция применяется на чистой БД, репозиторий проходит тесты против PostgreSQL, API-тесты на фейках, healthz отвечает.
- [ ] Волна 3: webhook принимает апдейт, `update_id` дедуплицируется в БД, фото уходит в MinIO, повтор апдейта не создаёт дубль.
- [ ] Волна 4: `next build` проходит, страница «Каталог» рендерит товары с сервера, картинки грузятся через rewrite, TMA-инициализация не падает в браузере.
- [ ] Волна 5: `docker compose up` поднимается с нуля, smoke-скрипт проходит, `--scale backend=3` не ломает каталог, README описывает запуск и webhook.
- [ ] Волна 6: полный `make check`, одно ревью всего diff, отчёт оператору, коммиты и push в GitHub.

## Решения оператора

| Вопрос | Ответ |
|--------|-------|
| GitHub: способ авторизации и имя репозитория | оператор пушит сам, репозиторий готовится локально с коммитами |
| Токен бота и публичный HTTPS-URL | запуск и секреты на операторе, в репозитории только `.env.example` и инструкции в README |
| Сценарий создания товара | без FSM, фото с подписью в любой момент |
| Масштабирование | nginx вынесен в отдельный overlay-файл, базовый compose публикует порты напрямую |
| Вёрстка | без CSS, только разметка |

## Отклонения (заполняется по ходу работы)

| # | Что уточнили | Почему |
|---|--------------|--------|
| 1 | добавлен `ReadProductImageUseCase` | отдача картинки требует проверки существования товара, в интерфейсах brief его не было |
| 2 | вместо передачи `Container` в хендлеры введён `ProductCommandsFactory` | иначе infrastructure импортирует composition и падает контракт import-linter |
| 3 | добавлена CLI-команда `wait-deps` | init-джоба не должна падать от гонки старта MinIO |
| 4 | образ `minio/minio` заменён на `bitnamilegacy/minio` | официальный образ недоступен в реестре этого окружения, сервер внутри тот же MinIO |
| 5 | nginx вынесен в `docker-compose.scale.yml` | базовый запуск не должен требовать лишнего контейнера |
| 6 | порты публикации вынесены в переменные `.env` | 8000 и 9000 заняты другим локальным проектом |
| 7 | повторная доставка во время обработки возвращает 503, а не 200 | иначе падение инстанса посередине обработки теряло бы апдейт навсегда |

## Волны работ

| Волна | Задачи | Слой | Файлы | Зависит от |
|-------|--------|------|-------|------------|
| 1 | скелет проекта, конфиг, домен, usecases, unit-тесты, import-linter | Domain + Application | `backend/pyproject.toml`, `domain/`, `application/`, `tests/unit/`, `.importlinter` | — |
| 2 | SQLAlchemy-модели, репозиторий, дедупликатор апдейтов, MinIO-адаптер, миграция, FastAPI-роуты, тесты | Infrastructure + Presentation | `infrastructure/db/`, `infrastructure/storage/`, `api/`, `migrations/`, `tests/integration/` | 1 |
| 3 | aiogram: dispatcher, middleware дедупликации, хендлеры, webhook-роут, CLI | Infrastructure + Presentation | `infrastructure/telegram/`, `api/routers/telegram.py`, `cli.py` | 2 |
| 4 | Next.js: layout, страница каталога, карточка, TMA-клиент, rewrites, Dockerfile | Presentation | `frontend/` | 2 |
| 5 | compose, nginx, init-джоба, Makefile, README, `.env.example`, smoke | Deploy | `docker-compose.yml`, `deploy/`, `Makefile`, `README.md` | 2, 3, 4 |
| 6 | полный прогон проверок, ревью diff, git init, коммиты, push | — | — | 1–5 |

Волны 2 и 4 можно вести параллельно после волны 1; волна 3 требует готового репозитория и MinIO-адаптера.

---

**Подтверждение:** ☑ подтверждено
