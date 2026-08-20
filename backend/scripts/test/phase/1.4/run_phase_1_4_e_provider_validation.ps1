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

Write-Host '[4/5] Knowledge Retrieval evaluation + quality gate'
& uv run python .\scripts\run_knowledge_retrieval_evaluation.py --k 3
if ($LASTEXITCODE -ne 0) { throw "Retrieval provider quality gate failed with exit code $LASTEXITCODE." }

Write-Host '[5/5] Validation summary'
Write-Host 'Phase 1.4-E provider validation suite completed.'
Write-Host 'Knowledge Retrieval source: PostgreSQL/pgvector knowledge_chunks.'
Write-Host 'Evaluation fixture JSON is test-data input only; retrieval results are never read from a JSON result file.'
Write-Host 'Mock Embedding + PostgreSQL/pgvector validates the deterministic local retrieval pipeline; it does not prove real model semantic quality.'
