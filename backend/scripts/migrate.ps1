[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "Enterprise AI Agent Platform - Database Migration" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor DarkGray

if (-not (Test-Path ".\.env")) {
    Write-Host "[WARN] backend/.env not found; Alembic will use its configured/default database URL." -ForegroundColor Yellow
}

Write-Host "[RUN ] alembic upgrade head" -ForegroundColor Cyan
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Database migration failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[ OK ] Database schema is up to date." -ForegroundColor Green
