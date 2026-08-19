$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Embedding Provider Validation'
Write-Host "Backend: $backend"
Write-Host '============================================================'

Write-Host '[RUN ] Embedding provider contract tests'
uv run pytest -q .\tests\test_embedding_provider.py
if ($LASTEXITCODE -ne 0) { throw "Embedding provider contract tests failed with exit code $LASTEXITCODE." }
Write-Host '[ OK ] Embedding provider contract tests'

Write-Host '[RUN ] Real embedding provider probe'
uv run python .\scripts\validate_embedding_provider.py
if ($LASTEXITCODE -ne 0) { throw "Real embedding provider probe failed with exit code $LASTEXITCODE." }
Write-Host '[ OK ] Real embedding provider probe'

Write-Host ''
Write-Host 'Validation completed.'
Write-Host 'Set EMBEDDING_PROVIDER=openai-compatible plus EMBEDDING_BASE_URL, EMBEDDING_API_KEY and EMBEDDING_MODEL in backend/.env to execute the real provider probe.'
