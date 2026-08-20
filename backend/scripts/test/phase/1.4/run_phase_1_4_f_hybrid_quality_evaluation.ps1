$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.4-F-03 Hybrid Quality"
Write-Host "Local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Retrieval / vector / hybrid contract regression"
uv run pytest -q tests/test_vector_knowledge_retrieval.py tests/test_hybrid_knowledge_retrieval.py tests/test_hybrid_knowledge_retrieval_service.py tests/test_hybrid_retrieval_api_contract.py
if ($LASTEXITCODE -ne 0) { throw "Retrieval contract tests failed." }

Write-Host "[2/3] Real PostgreSQL/pgvector hybrid quality evaluation"
Write-Host "Fixture JSON is test input only. Rankings are produced by the real FastAPI Retrieval API backed by PostgreSQL/pgvector."
Write-Host "If no real embedding provider is configured, EMBEDDING_PROVIDER=mock is allowed for deterministic local embeddings."
uv run python .\scripts\run_phase_1_4_f_hybrid_quality_evaluation.py
if ($LASTEXITCODE -ne 0) { throw "F-03 hybrid quality gate failed." }

Write-Host "[3/3] Full backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Full backend regression failed." }

Write-Host "============================================================"
Write-Host "Phase 1.4-F-03 local validation completed."
Write-Host "No GitHub Actions workflow is invoked by this script."
Write-Host "============================================================"
