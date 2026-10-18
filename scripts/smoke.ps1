#!/usr/bin/env pwsh
# Поднимает compose и проверяет живые эндпоинты.
param(
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$healthUrl = "http://localhost:$BackendPort/api/healthz"
$productsUrl = "http://localhost:$BackendPort/api/products"
$imageUrl = "http://localhost:$BackendPort/api/products/00000000-0000-0000-0000-000000000000/image"

Push-Location $root
try {
    docker compose up -d --build

    Write-Host "waiting for backend..."
    $deadline = (Get-Date).AddMinutes(3)
    $healthy = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $healthUrl -TimeoutSec 3
            if ($response.StatusCode -eq 200) { $healthy = $true; break }
        }
        catch {
            Start-Sleep -Seconds 2
        }
    }

    if (-not $healthy) {
        docker compose ps -a
        throw "backend did not become healthy in time"
    }

    $health = Invoke-RestMethod -Uri $healthUrl
    Write-Host ("health: " + ($health | ConvertTo-Json -Compress))

    $catalog = Invoke-RestMethod -Uri $productsUrl
    Write-Host ("products: " + $catalog.items.Count + " item(s)")

    try {
        Invoke-WebRequest -UseBasicParsing -Uri $imageUrl -TimeoutSec 5 | Out-Null
        throw "expected 404 for unknown product image"
    }
    catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -ne 404) { throw "unexpected status for unknown image: $statusCode" }
        Write-Host "unknown image returns 404: ok"
    }

    docker compose ps
    Write-Host "smoke passed" -ForegroundColor Green
}
finally {
    Pop-Location
}
