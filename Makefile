.PHONY: check up down scale logs smoke

check:
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	cd backend && uv run mypy src tests
	cd backend && uv run lint-imports
	cd backend && uv run pytest
	cd frontend && npm run build

up:
	docker compose up -d --build

down:
	docker compose down

scale:
	docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --build --scale backend=3 --scale frontend=2

logs:
	docker compose logs -f backend

smoke:
	powershell -NoProfile -ExecutionPolicy Bypass -File ./scripts/smoke.ps1
