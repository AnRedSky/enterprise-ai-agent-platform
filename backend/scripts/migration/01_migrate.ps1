$ErrorActionPreference = "Stop"
Write-Host "[1/2] Upgrade database to head"
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
Write-Host "[2/2] Verify migration head"
uv run alembic current
if ($LASTEXITCODE -ne 0) { throw "Migration head verification failed." }
