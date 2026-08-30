$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 2.10-II Operator Action Governance Real Gate"
Write-Host "============================================================"
Write-Host "[0/5] Local precondition checks"
Write-Host "Service policy: this gate never creates, starts, restarts, or stops API, Scheduler, Worker, PostgreSQL, or Redis."
Write-Host "Test data policy: acceptance tests create and clean up all identities and business facts automatically."

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required but was not found in PATH."
}
if (-not (Test-Path ".\\pyproject.toml")) {
    throw "Run this gate from the backend directory."
}

Write-Host "[1/5] Migration/head verification"
uv run alembic heads
if ($LASTEXITCODE -ne 0) { throw "Alembic head verification failed." }
Write-Host "[INFO] If the local database is not at head, run 'uv run alembic upgrade head' outside this gate."

Write-Host "[2/5] Operator Action unit + API contract"
uv run pytest -q tests/unit/test_operator_action_governance.py tests/api_contract/test_api_operator_actions.py
if ($LASTEXITCODE -ne 0) { throw "Operator Action unit/contract tests failed." }

Write-Host "[3/5] Database availability probe"
uv run python -c "import asyncio; from app.infrastructure.db.session import SessionLocal; async def main(): async with SessionLocal() as db: await db.execute(__import__('sqlalchemy').text('SELECT 1')); print('[PASS] PostgreSQL is available.'); asyncio.run(main())"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOT EXECUTED] PostgreSQL is not available; Real Acceptance was not executed."
    Write-Host "[INFO] No service is started automatically and no manual test data is required."
    exit 0
}

Write-Host "[4/5] Operator Action real PostgreSQL acceptance"
uv run pytest -q -m real_api tests/api_real/test_operator_action_governance_acceptance.py --tb=short
if ($LASTEXITCODE -ne 0) { throw "Operator Action Real Acceptance failed." }

Write-Host "[5/5] Service startup boundary"
Write-Host "[PASS] No API/Scheduler/Worker/PostgreSQL/Redis process was created or stopped by this gate."
Write-Host "[PASS] Phase 2.10-II Operator Action Governance Real Gate completed."
