$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - PostgreSQL + pgvector Validation'
Write-Host "Backend: $backend"
Write-Host '============================================================'

Write-Host '[RUN ] Vector provider contract tests'
uv run pytest -q .\tests\test_vector_retrieval_provider.py
if ($LASTEXITCODE -ne 0) { throw "Vector provider contract tests failed with exit code $LASTEXITCODE." }
Write-Host '[ OK ] Vector provider contract tests'

Write-Host '[RUN ] Database / alembic upgrade head'
uv run alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed with exit code $LASTEXITCODE." }
Write-Host '[ OK ] Database migration'

Write-Host '[RUN ] PostgreSQL + pgvector round-trip probe'
uv run python .\scripts\validate_pgvector.py
if ($LASTEXITCODE -ne 0) { throw "pgvector validation failed with exit code $LASTEXITCODE." }
Write-Host '[ OK ] PostgreSQL + pgvector round-trip probe'

Write-Host ''
Write-Host 'Validation completed.'
Write-Host 'Set VECTOR_PROVIDER=pgvector and VECTOR_DB_URL in backend/.env to execute the real probe.'
