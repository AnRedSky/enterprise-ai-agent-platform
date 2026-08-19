$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host "Enterprise AI Agent Platform - Phase 1.4-F Retrieval DB Loop"
Write-Host "Local manual validation only"
Write-Host "============================================================"

Write-Host "[1/3] Retrieval / vector / hybrid unit-contract regression"
uv run pytest -q tests/test_vector_knowledge_retrieval.py tests/test_hybrid_knowledge_retrieval.py tests/test_hybrid_knowledge_retrieval_service.py tests/test_hybrid_retrieval_api_contract.py
if ($LASTEXITCODE -ne 0) { throw "Retrieval contract tests failed." }

Write-Host "[2/3] Real PostgreSQL/pgvector database loop"
Write-Host "The loop uses real DB + ingestion + vector indexing + FastAPI retrieval + hybrid fusion + citation hydration."
Write-Host "If no real embedding provider is configured, set EMBEDDING_PROVIDER=mock for deterministic local embedding only."
uv run python .\scripts\run_phase_1_4_f_retrieval_db_loop.py
if ($LASTEXITCODE -ne 0) { throw "Retrieval database loop validation failed." }

Write-Host "[3/3] Full backend regression"
uv run pytest -q
if ($LASTEXITCODE -ne 0) { throw "Full backend regression failed." }

Write-Host "============================================================"
Write-Host "Phase 1.4-F Retrieval DB loop validation completed."
Write-Host "No GitHub Actions workflow is invoked by this script."
Write-Host "============================================================"
