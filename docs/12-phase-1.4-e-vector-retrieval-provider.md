# Phase 1.4-E：Vector Retrieval Provider 深化

> 本文记录 Phase 1.4-E 从真实 Embedding Provider 验证进入 Vector Retrieval Provider contract 的实施基线。当前仍为本地开发 / 测试阶段，不执行 GitHub Actions CI。

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

具体 Vector DB（例如 pgvector、Milvus）不得直接进入 Runtime 业务代码。

## 2. 已实现

### VectorRetrievalProvider contract

提供：

- `upsert(records)`
- `search(query_embedding, top_k, min_score)`
- `VectorRecord`
- `VectorSearchResult`
- `VectorRetrievalProviderError`

结果保持 provider-neutral：

```text
chunk_id
score
metadata
```

### Local deterministic adapter

`InMemoryVectorRetrievalProvider` 用于：

- contract tests
- cosine similarity 验证
- stable tie-breaking
- `top_k` / `min_score` 验证
- embedding dimension mismatch 验证

该实现**仅用于本地测试，不作为生产 Vector DB**。

## 3. 配置

后端 `Settings` 已增加：

```text
VECTOR_PROVIDER=none
VECTOR_DB_URL=
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

真实配置只写入本地 `backend/.env`。Git 仓库只维护 `backend/.env.example`。

推荐本地配置流程：

```powershell
cd backend
Copy-Item .env.example .env
```

如果已有 `.env`，只补充上述 `VECTOR_*` 参数即可。

不要把真实 API Key、Vector DB 密码、带凭据的连接 URL 提交到 Git。

## 4. 当前测试

开发者本地同步代码后执行：

```powershell
cd backend
uv sync
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py
```

真实 Embedding Provider：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_embedding_provider_validation.ps1
```

真实 Provider 未配置时，probe 可以正常 skip；contract tests 必须通过。

## 5. 下一步

下一任务不是直接绑定某个 Vector DB，而是增加真实 Vector DB adapter contract：

1. 定义 Vector DB adapter 生命周期与连接配置
2. 明确 collection / index / dimension contract
3. 增加批量 upsert / search 边界
4. 增加 metadata filter contract
5. 增加权限过滤与 Knowledge Base scope
6. 将 embedding dimension 检查前置到 ingestion/indexing 阶段
7. 再选择 pgvector 作为第一真实实现
8. 用 Evaluation Dataset 对比 lexical-v2 与 vector retrieval
9. 最后再进入 hybrid retrieval

## 6. 不在当前任务实现

- 不直接接入生产 Vector DB
- 不新增 CI workflow
- 不把 Vector DB SDK 暴露给 Runtime
- 不改变现有 lexical-v2 API contract
- 不提交本地 `.env`
