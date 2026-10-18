#!/usr/bin/env pwsh
# Полный прогон проверок: backend (стиль, типы, слои, тесты) и frontend (сборка).
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot

Push-Location (Join-Path $root "backend")
try {
    uv sync
    uv run ruff format --check .
    uv run ruff check .
    uv run mypy src tests
    uv run lint-imports
    uv run pytest
}
finally {
    Pop-Location
}

Push-Location (Join-Path $root "frontend")
try {
    npm ci --no-fund --no-audit
    npm run build
}
finally {
    Pop-Location
}

Write-Host "all checks passed" -ForegroundColor Green
