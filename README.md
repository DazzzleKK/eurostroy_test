# Eurostroy Catalog

Тестовое задание: микросервис каталога с админским ботом и Telegram Mini App.

Админ присылает боту фото с названием в подписи. Фото уходит в MinIO, запись
в PostgreSQL. Каталог открывается страницей Next.js в браузере и кнопкой
Mini App внутри Telegram.

## Стек

- backend: FastAPI, aiogram 3, SQLAlchemy 2 + asyncpg, Alembic, MinIO client
- frontend: Next.js 15 (App Router), TypeScript, без CSS-фреймворков
- инфраструктура: PostgreSQL 16, MinIO, Docker Compose, nginx (опционально)

## Структура

```
backend/
  src/eurostroy/
    domain/            сущность товара, ошибки, порты
    application/       usecases: создать, список, картинка, курсор
    infrastructure/    PostgreSQL, MinIO, aiogram, часы и id
    api/               FastAPI: роуты, схемы, обработка ошибок
    composition.py     сборка зависимостей
    cli.py             wait-deps, ensure-bucket, set-webhook
  migrations/          Alembic
  tests/               unit + integration (фейки и живой PostgreSQL)
frontend/
  app/                 layout, страница каталога, прокси /api
  components/          инициализация Telegram WebApp
  lib/api.ts           запрос каталога с сервера
scripts/               check.ps1 и smoke.ps1
deploy/nginx.conf
docker-compose.yml
docker-compose.scale.yml
```

## Как устроено

Слои идут в одну сторону: `domain <- application <- api`, инфраструктура
реализует порты домена. Направление проверяет `import-linter`, поэтому
падение контракта ломает `check`.

Отказоустойчивость построена на трёх решениях:

1. В памяти процессов нет состояния: сессия базы живёт один вызов usecase,
   картинки не кэшируются на диске, FSM бота не используется.
2. Идемпотентность апдейтов через таблицу `telegram_updates`. Вставка идёт
   одним `INSERT ... ON CONFLICT`, поэтому повторная доставка от Telegram
   не создаёт второй товар и не требует блокировок между инстансами.
   Если тот же апдейт ещё в работе у другого инстанса, вебхук отвечает 503,
   и Telegram повторяет доставку позже. Отвечать в этот момент 200 нельзя:
   падение обработчика потеряло бы апдейт навсегда.
3. Миграции, создание бакета и установка вебхука вынесены в CLI и init-джобу.
   Если делать это в `on_startup`, каждый инстанс выполнял бы одно и то же
   одновременно.

Картинки отдаёт backend (`/api/products/{id}/image`), а не MinIO напрямую:
бакет остаётся закрытым, не нужны пресайн-URL с истекающим сроком, и адреса
остаются относительными. Frontend проксирует `/api/*` к backend, поэтому
страница и картинки живут на одном origin и внутри Telegram WebView.

Бот не ведёт диалог: фото с подписью от админа принимается в любой момент.
Это осознанный компромисс ради stateless-инстансов. Обработка апдейта идёт
inline в запросе вебхука, очередь задач в задание не входила.

## Быстрый старт в Docker

Нужен Docker Desktop.

1. Создайте `.env` из примера и заполните токен и админов:

   ```powershell
   Copy-Item .env.example .env
   ```

   Минимум:

   ```
   BOT_TOKEN=123456:AA...
   ADMIN_IDS=111111111
   BOT_WEBHOOK_SECRET=любая-случайная-строка
   ```

2. Поднимите стенд:

   ```powershell
   docker compose up -d --build
   ```

3. Проверьте:

   - каталог: http://localhost:3000
   - API: http://localhost:8000/api/products
   - health: http://localhost:8000/api/healthz
   - MinIO console: http://localhost:9001 (minioadmin / minioadmin)

4. В Telegram найдите своего бота, отправьте `/start`. Бот ответит
   «У меня есть товар» и кнопкой «Открыть каталог». Админу дополнительно
   показывается кнопка «Создать товар» (то же самое делает команда `/new`):
   она подсказывает формат, а товар создаётся любым последующим фото
   с названием в подписи.

Бот работает только через вебхук, фонового опроса нет. Для локальной
проверки каталога этого достаточно, для бота нужен публичный HTTPS, шаг ниже.

## Публичный HTTPS, вебхук и Mini App

Telegram требует HTTPS для вебхука и для кнопки Mini App. Проще всего один
туннель на nginx, который отдаёт и фронтенд, и API:

1. Запустите стенд с nginx:

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --build
   ```

   Каталог будет на http://localhost:8080.

2. Поднимите туннель:

   ```powershell
   cloudflared tunnel --url http://localhost:8080
   ```

   Возьмите выданный `https://...trycloudflare.com`.

3. Впишите этот адрес в `.env` и перезапустите backend:

   ```
   PUBLIC_API_URL=https://<туннель>
   WEBAPP_URL=https://<туннель>
   ```

   ```powershell
   docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d
   ```

4. Установите вебхук:

   ```powershell
   docker compose exec backend python -m eurostroy.cli set-webhook
   ```

5. Проверьте:

   ```powershell
   docker compose exec backend python -m eurostroy.cli webhook-info
   ```

Адрес туннеля живёт до перезапуска `cloudflared`. После смены адреса
повторите шаги 3 и 4. Для постоянного адреса нужен именованный туннель
или собственный домен с сертификатом.

Кнопка «Открыть каталог» использует `WEBAPP_URL`, поэтому Mini App открывает
именно публичный адрес. Кнопку меню бота можно продублировать в BotFather
(`/setmenubutton`), но это необязательно.

Порты публикуются через переменные `BACKEND_PORT`, `FRONTEND_PORT`,
`MINIO_PORT`, `MINIO_CONSOLE_PORT`, `GATEWAY_PORT`. Если 3000 или 8000 заняты
другим проектом, поменяйте их в `.env`.

## Локальная разработка без Docker

Backend:

```powershell
cd backend
uv sync
$env:DATABASE_URL="postgresql+asyncpg://catalog:catalog@localhost:5432/catalog"
uv run alembic upgrade head
uv run python -m eurostroy.cli ensure-bucket
uv run uvicorn eurostroy.main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

PostgreSQL и MinIO можно поднять отдельно:

```powershell
docker compose up -d postgres minio
```

`BACKEND_INTERNAL_URL` по умолчанию `http://localhost:8000`, этого хватает
для `npm run dev`.

## Проверки

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke.ps1
```

Скрипты написаны под PowerShell 5.1, отдельный `pwsh` не нужен. Если порт
backend не 8000, передайте его в smoke: `-BackendPort 8010`.

Или по отдельности:

```powershell
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run lint-imports
uv run pytest
```

Тест репозитория против настоящего PostgreSQL включается переменной:

```powershell
docker compose up -d postgres
$env:TEST_DATABASE_URL="postgresql+asyncpg://catalog:catalog@localhost:5432/catalog"
uv run pytest tests/integration/test_repository_pg.py
```

Если порт 5432 занят локальным PostgreSQL, `docker compose` не поднимет
контейнер. Тогда поменяйте порт в `docker-compose.yml` или остановите
локальный сервер.

## Масштабирование

Обычный запуск публикует порты 3000 и 8000 напрямую.

Запуск в несколько инстансов за nginx:

```powershell
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --build `
  --scale backend=3 --scale frontend=2
```

Что происходит:

- backend и frontend не публикуют порты, наружу смотрит только nginx:8080;
- nginx распределяет запросы между инстансами по DNS Docker;
- состояние живёт только в PostgreSQL и MinIO, поэтому инстансы
  взаимозаменяемы;
- вебхук можно направить на любой инстанс, дубли отсекаются по `update_id`.

Проверка, что дублей нет: отправьте `update_id` повторно через тест
`tests/unit/test_dedupe_middleware.py` или через интеграционный тест с базой.
Вручную это делается так: `docker compose logs backend` после ретрая не должен
показывать второй «Товар добавлен».

## API

```
GET  /api/products?limit=20&cursor=...
GET  /api/products/{id}/image
GET  /api/healthz
POST /api/telegram/webhook
```

Ошибки в одном формате:

```json
{"error": {"code": "validation_failed", "message": "Некорректный курсор"}}
```

Коды: `validation_failed` (400), `product_not_found` (404), `image_too_large`
(413), `unsupported_image` (415).

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_URL` | строка подключения к PostgreSQL | `postgresql+asyncpg://catalog:catalog@postgres:5432/catalog` |
| `DB_POOL_SIZE` | размер пула соединений | `5` |
| `S3_ENDPOINT` | адрес MinIO | `minio:9000` |
| `S3_ACCESS_KEY`, `S3_SECRET_KEY` | ключи MinIO | `minioadmin` |
| `S3_BUCKET` | бакет для картинок | `catalog` |
| `S3_SECURE` | TLS до S3 | `false` |
| `BOT_TOKEN` | токен бота | пусто, бот выключен |
| `BOT_WEBHOOK_SECRET` | секрет вебхука | `change-me` |
| `PUBLIC_API_URL` | публичный адрес backend | `http://localhost:8000` |
| `WEBAPP_URL` | публичный адрес фронтенда для Mini App | `http://localhost:3000` |
| `ADMIN_IDS` | id админов через запятую | пусто |
| `BACKEND_INTERNAL_URL` | адрес backend для Next.js | `http://localhost:8000` |

Свой id можно узнать у бота `@userinfobot`.

## Ограничения

- Нет редактирования и удаления товаров.
- Нет очереди: апдейт обрабатывается в запросе вебхука. При больших файлах
  это упрётся в таймаут, тогда нужна очередь.
- Осиротевшие объекты в MinIO не удаляются, если запись в базу не удалась.
- Каталог публичный, отдельной авторизации у веб-страницы нет.
- Пагинация по курсору реализована в API, но на странице показываются
  последние 100 товаров.

## Если что-то не работает

- `healthz` отвечает 503: смотрите `docker compose logs backend`,
  проверьте, что init-джоба прошла (`docker compose ps -a`).
- Вебхук отвечает 401: `BOT_WEBHOOK_SECRET` в `.env` и в Telegram не совпадают,
  переустановите вебхук после правки.
- Mini App не открывается: `WEBAPP_URL` должен быть HTTPS и доступен
  из интернета, а не `localhost`.
- Картинки 404: бакет пуст или init-джоба не выполнила `ensure-bucket`.
- MinIO отвечает отказом после смены пароля: ключи хранятся в томе
  `minio-data`, старые данные не перешифровываются. Для чистого старта
  выполните `docker compose down -v` и поднимите стенд заново.
