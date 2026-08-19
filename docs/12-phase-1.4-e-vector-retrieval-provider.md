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

`InMemoryVectorRetrievalProvider` 用于 contract tests，覆盖：

- cosine similarity
- stable tie-breaking
- `top_k` / `min_score`
- embedding dimension mismatch
- Knowledge Base scope

### PostgreSQL + pgvector adapter

新增 `PgVectorRetrievalProvider`，保持 SQLAlchemy / PostgreSQL 细节隔离在 adapter 层。

当前实现提供：

- batch sequential upsert / update
- pgvector cosine distance (`<=>`)
- `score = 1 - cosine_distance`
- top-k 排序
- min-score filtering
- Knowledge Base scope filtering
- embedding dimension validation
- `knowledge_base_id` / `document_version_id` metadata contract

### Database migration

新增 `0010_pgvector_knowledge_chunks`：

- `CREATE EXTENSION IF NOT EXISTS vector`
- `knowledge_chunks` vector storage table
- configurable `EMBEDDING_DIMENSION`
- HNSW cosine index
- Knowledge Base / Document Version scope indexes
- chunk cascade cleanup

Migration 通过项目统一入口执行：

```powershell
cd backend
uv run alembic upgrade head
```

## 3. 配置

`backend/.env` 本地建议：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-embedding-provider/v1
EMBEDDING_API_KEY=your-local-key
EMBEDDING_MODEL=your-embedding-model
EMBEDDING_TIMEOUT_SECONDS=30
EMBEDDING_DIMENSION=1536

VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

`EMBEDDING_DIMENSION` 必须与真实 Embedding Provider 返回向量维度一致，并且 migration 0010 创建的 pgvector column 维度保持一致。

真实 `.env`、API Key、数据库密码和带凭据的连接 URL 不提交 Git；仓库只维护 `.env.example`。

## 4. 本地验证顺序

### 4.1 Contract

```powershell
cd backend
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py
```

### 4.2 Schema

```powershell
uv run alembic upgrade head
```

### 4.3 pgvector round-trip

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pgvector_validation.ps1
```

未配置 `VECTOR_PROVIDER=pgvector` 时允许 skip；配置后必须完成：

```text
PostgreSQL
  ↓
vector extension
  ↓
knowledge_chunks
  ↓
upsert
  ↓
cosine search
  ↓
Knowledge Base scope
  ↓
cleanup
```

### 4.4 Embedding

真实 Embedding Provider 仍使用：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_embedding_provider_validation.ps1
```

## 5. 设计约束

- 不把 pgvector SQL operator 暴露给 Runtime。
- 不修改 lexical-v2 API contract。
- Vector score 使用统一 cosine similarity 语义。
- Knowledge Base scope 必须在 Vector DB 查询层过滤，不能只依赖上层结果裁剪。
- Embedding dimension 在写入与查询前校验。
- 当前先实现 PostgreSQL + pgvector，不引入第二种 Vector DB。
- 不执行 GitHub Actions CI。

## 6. 下一步

pgvector 本地 round-trip 验证通过后继续：

1. 将真实 Embedding Provider 接入 ingestion/indexing。
2. Document Chunk → Embedding → pgvector upsert 建立真实索引链路。
3. Retrieval API 增加 vector retrieval mode。
4. 使用 Evaluation Dataset 对比 lexical-v2 / vector retrieval 的 Recall@K、Precision@K、MRR。
5. 稳定后进入 hybrid retrieval（lexical + vector）。
