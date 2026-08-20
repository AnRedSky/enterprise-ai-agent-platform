$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.4-F Hybrid Retrieval"
Write-Host "Local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Hybrid retrieval contract tests"
uv run pytest -q tests/test_hybrid_knowledge_retrieval.py
if ($LASTEXITCODE -ne 0) { throw "Hybrid retrieval contract tests failed." }

Write-Host "[2/3] Database-backed hybrid retrieval service tests"
uv run pytest -q tests/test_hybrid_knowledge_retrieval_service.py tests/test_hybrid_retrieval_api_contract.py tests/test_vector_knowledge_retrieval.py
if ($LASTEXITCODE -ne 0) { throw "Hybrid retrieval service/API tests failed." }

Write-Host "[3/3] Full backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Full backend regression failed." }

Write-Host "============================================================"
Write-Host "Phase 1.4-F local validation completed."
Write-Host "For real hybrid retrieval, ensure PostgreSQL/pgvector and a real"
Write-Host "OpenAI-compatible embedding provider are configured in backend/.env."
Write-Host "============================================================"
