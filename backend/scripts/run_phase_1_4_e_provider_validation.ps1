$ErrorActionPreference = 'Stop'

$backend = Split-Path -Parent $PSScriptRoot
Set-Location $backend

Write-Host '============================================================'
Write-Host 'Enterprise AI Agent Platform - Phase 1.4-E Provider Validation'
Write-Host "Backend: $backend"
Write-Host '============================================================'

Write-Host '[1/5] Embedding provider contract + real provider probe'
& .\scripts\run_embedding_provider_validation.ps1
if ($LASTEXITCODE -ne 0) { throw "Embedding provider validation failed with exit code $LASTEXITCODE." }

Write-Host '[2/5] PostgreSQL + pgvector contract + round-trip probe'
& .\scripts\run_pgvector_validation.ps1
if ($LASTEXITCODE -ne 0) { throw "pgvector validation failed with exit code $LASTEXITCODE." }

Write-Host '[3/5] Full backend regression'
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Backend regression failed with exit code $LASTEXITCODE." }

Write-Host '[4/5] Provider evaluation input check'
$results = Join-Path $backend 'evaluation\vector_results.jsonl'
if (Test-Path $results) {
    Write-Host "Found provider results: $results"
    uv run python .\scripts\evaluate_knowledge_retrieval_provider.py $results
    if ($LASTEXITCODE -ne 0) { throw "Retrieval provider quality gate failed with exit code $LASTEXITCODE." }
} else {
    Write-Host 'Provider results not found; quality gate remains pending.'
    Write-Host 'Run the vector retrieval scenario with the real provider and save results to:'
    Write-Host $results
}

Write-Host '[5/5] Validation summary'
Write-Host 'Phase 1.4-E provider validation suite completed.'
Write-Host 'A missing vector_results.jsonl means real Retrieval Evaluation is still pending.'
