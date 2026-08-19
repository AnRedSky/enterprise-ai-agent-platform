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

$provider = (uv run python -c "from app.core.config import settings; print(settings.embedding_provider)").Trim()

if ($provider -eq 'mock') {
    Write-Host '[RUN ] Deterministic mock embedding validation'
    uv run pytest -q .\tests\test_mock_embedding_provider.py
    if ($LASTEXITCODE -ne 0) { throw "Mock embedding validation failed with exit code $LASTEXITCODE." }
    Write-Host '[ OK ] Deterministic mock embedding validation'
} else {
    Write-Host '[RUN ] Real embedding provider probe'
    uv run python .\scripts\validate_embedding_provider.py
    if ($LASTEXITCODE -ne 0) { throw "Real embedding provider probe failed with exit code $LASTEXITCODE." }
    Write-Host '[ OK ] Real embedding provider probe'
}

Write-Host ''
if ($provider -eq 'mock') {
    Write-Host 'Validation completed in offline mock mode.'
    Write-Host 'Mock mode validates the embedding contract and deterministic pipeline only; it does not prove real model semantic quality.'
} else {
    Write-Host 'Validation completed with the configured real embedding provider.'
    Write-Host 'Set EMBEDDING_PROVIDER=mock for offline validation when no real provider credentials are available.'
}
