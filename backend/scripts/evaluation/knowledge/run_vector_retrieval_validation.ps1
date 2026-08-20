$ErrorActionPreference = 'Stop'

Write-Host '=== Phase 1.4-E Vector Retrieval validation ==='
Write-Host '1) Contract tests'
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py tests/test_knowledge_vector_indexing.py tests/test_vector_knowledge_retrieval.py

Write-Host '2) Full backend regression'
uv run pytest -q

Write-Host '3) Optional pgvector schema check'
$compose = docker compose ps --services --filter 'status=running' | Select-String '^postgres$'
if ($compose) {
    uv run alembic upgrade head
    Write-Host 'PostgreSQL service is running; migrations are up to date.'
} else {
    Write-Host 'PostgreSQL is not running; skipped pgvector migration check.'
    Write-Host 'Start it with: docker compose up -d postgres redis'
}

Write-Host '=== Validation complete ==='
Write-Host 'For real Vector retrieval, configure backend/.env with EMBEDDING_PROVIDER=openai-compatible and VECTOR_PROVIDER=pgvector, then exercise POST /api/v1/knowledge/retrieve with mode=vector.'
