$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.4-G-01 Retrieval Debug"
Write-Host "Local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Hybrid backend contract regression"
& uv run pytest -q tests/test_hybrid_knowledge_retrieval.py tests/test_hybrid_retrieval_api_contract.py tests/test_hybrid_knowledge_retrieval_service.py
if ($LASTEXITCODE -ne 0) { throw "Hybrid backend contract tests failed." }

Write-Host "[2/3] Frontend Retrieval Debug contract"
Push-Location (Join-Path $PSScriptRoot "..\..\frontend")
try {
    & npm test -- --run tests/views/knowledge/KnowledgeWorkbench.test.ts
    if ($LASTEXITCODE -ne 0) { throw "Frontend Retrieval Debug tests failed." }

    Write-Host "[3/3] Frontend production build"
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
} finally {
    Pop-Location
}

Write-Host "============================================================"
Write-Host "Phase 1.4-G-01 local validation completed."
Write-Host "Hybrid score breakdown is returned by the backend API and displayed by Retrieval Debug."
Write-Host "No GitHub Actions workflow is invoked by this script."
Write-Host "============================================================"
