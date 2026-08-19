# Phase 1.4-E：Vector Retrieval Provider 深化

> 当前阶段仍为本地开发 / 测试阶段，不执行 GitHub Actions CI。Backend 统一使用 `uv` 项目环境。

## 1. 本阶段目标

建立与具体 Vector DB 解耦的向量检索边界：

```text
Query
  ↓
Embedding Provider
  ↓
query embedding
  ↓
Vector Retrieval Provider
  ↓
provider-neutral VectorSearchResult
  ↓
Knowledge Retrieval / Citation
```

具体 Vector DB 不得直接进入 Runtime 业务代码。

## 2. 已完成

### Provider-neutral contract

提供：

- `upsert(records)`
- `search(query_embedding, top_k, min_score, knowledge_base_id)`
- `VectorRecord`
- `VectorSearchResult`
- `VectorRetrievalProviderError`

### Local deterministic adapter

`InMemoryVectorRetrievalProvider` 用于 contract tests，覆盖 cosine similarity、stable tie-breaking、`top_k` / `min_score`、dimension mismatch、Knowledge Base scope。

### PostgreSQL + pgvector adapter

`PgVectorRetrievalProvider` 已落地，隔离 SQLAlchemy / PostgreSQL 细节，并支持 batch upsert、cosine distance、top-k、min-score、Knowledge Base scope、dimension validation 与 metadata contract。

### 真实索引链路（本次新增）

新增 `KnowledgeVectorIndexingService`：

```text
Document Chunk
  ↓
OpenAI-compatible Embedding
  ↓
Embedding batch
  ↓
VectorRecord
  ↓
PgVectorRetrievalProvider.upsert
  ↓
knowledge_chunks
```

- `VECTOR_PROVIDER=none` 时保持兼容，vector index status 为 `skipped`。
- `VECTOR_PROVIDER=pgvector` 时要求 `EMBEDDING_PROVIDER=openai-compatible`。
- Embedding API 按 `EMBEDDING_BATCH_SIZE` 分批。
- `KnowledgeDocumentVersion.vector_index_status`：`pending / processing / ready / skipped / failed`。
- 保存实际 `embedding_model`，便于后续重建索引和排障。
- Chunk 持久化与 Vector indexing 分成两个可恢复阶段；向量索引失败不会删除已经持久化的 chunks。

### Database migration

- `0010_pgvector_knowledge_chunks`：pgvector extension、vector table、dimension、HNSW index。
- `0011_knowledge_vector_index_status`：增加 vector indexing 状态与 embedding model。

Migration：

```powershell
cd backend
uv run alembic upgrade head
```

**重要：migration 0010 要求 PostgreSQL 服务端已经安装 pgvector。** Python / `uv` 环境不能替 PostgreSQL 安装 `vector` extension。本项目 Docker Compose 默认使用 `pgvector/pgvector:pg16`。

## 3. 配置

`backend/.env` 在需要真实索引时配置：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-embedding-provider/v1
EMBEDDING_API_KEY=your-local-key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_TIMEOUT_SECONDS=30
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=32

VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

`EMBEDDING_DIMENSION` 必须与真实 Provider 返回维度以及 migration 0010 的 vector column 一致。

真实 `.env`、API Key、数据库密码和带凭据连接 URL 不提交 Git；仓库只维护 `.env.example`。

## 4. 本地验证顺序

### 4.1 Contract

```powershell
cd backend
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py tests/test_knowledge_vector_indexing.py
```

### 4.2 PostgreSQL / pgvector Schema

```powershell
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
```

### 4.3 pgvector round-trip

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pgvector_validation.ps1
```

### 4.4 真实 Embedding Provider

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_embedding_provider_validation.ps1
```

### 4.5 真实 Chunk → Embedding → pgvector indexing

在 `backend/.env` 同时设置：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=...
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=...
VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
```

然后执行现有 Runtime / Knowledge 联调脚本，确认 ingest 返回：

```json
{
  "ingestion_status": "ready",
  "vector_index_status": "ready",
  "embedding_model": "..."
}
```

并在 PostgreSQL 检查：

```sql
SELECT count(*) FROM knowledge_chunks;
```

## 5. 设计约束

- 不把 pgvector SQL operator 暴露给 Runtime。
- 不修改 lexical-v2 API contract。
- Vector score 使用统一 cosine similarity 语义。
- Knowledge Base scope 必须在 Vector DB 查询层过滤。
- Embedding dimension 在写入与查询前校验。
- Vector indexing 与 chunk ingestion 分阶段，可独立失败/重试。
- 当前只实现 PostgreSQL + pgvector，不引入第二种 Vector DB。
- 本地开发统一使用 `uv run`，不直接使用系统 Python / pip。
- 不执行 GitHub Actions CI。

## 6. 下一步

1. Retrieval API 增加 `mode=vector`，复用现有 RBAC / Citation contract。
2. Query → Embedding → pgvector search → Chunk/Citation 形成真实 vector retrieval 闭环。
3. 使用现有 5 条 Evaluation Dataset 对 lexical-v2 / vector retrieval 做 Recall@K、Precision@K、MRR 对比。
4. 稳定后进入 hybrid retrieval（lexical + vector）。
