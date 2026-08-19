# Phase 1.4-E：Vector Retrieval 真实闭环与验收

## 1. 本阶段已落地

当前 `main` 已具备 provider-neutral Vector Retrieval contract、PostgreSQL + pgvector adapter、真实 Embedding indexing service，以及 `POST /api/v1/knowledge/{knowledge_base_id}/documents/{document_id}/versions/{version_id}/vector-index` 重建入口。

真实检索链路：

```text
query
  ↓
OpenAI-compatible Embedding
  ↓
query embedding
  ↓
PgVectorRetrievalProvider.search
  ↓
Knowledge Base / Document / Version authorization hydration
  ↓
Chunk / Citation
```

检索 API：

```http
POST /api/v1/knowledge/retrieve
```

请求新增：

```json
{
  "query": "企业 Agent Runtime",
  "top_k": 5,
  "min_score": 0.0,
  "mode": "vector",
  "fallback_to_lexical": false
}
```

`mode`：

- `lexical-v2`：现有确定性 lexical retrieval，默认值。
- `vector`：真实 Embedding + pgvector。

`fallback_to_lexical=true` 时，Vector Provider / Embedding 失败才显式降级到 `lexical-v2`，响应会返回 `fallback_used=true`。默认不降级，避免真实 Vector 检索失败后被静默伪装成 lexical 成功。

## 2. Index 状态机

`KnowledgeDocumentVersion.vector_index_status`：

```text
pending → processing → ready
                    ↘ failed

VECTOR_PROVIDER=none → skipped
```

`embedding_model` 保存本次索引实际使用的模型名称，便于模型切换后的重建与故障排查。

Chunk ingestion 与 Vector indexing 是两个可恢复阶段：Chunk 已持久化但 Vector indexing 失败时，不删除 Chunk；可以重新调用 vector-index endpoint。

## 3. 增量与重建策略

### 增量原则

- Chunk 使用 `content_hash` 标识内容变化。
- 相同 Version 的重复索引使用 `upsert`，不会产生重复 vector row。
- 新 Version 重新生成 Chunk 后，以新 Version 的 Chunk 集合建立索引。
- 后续可基于 `content_hash + embedding_model + embedding_dimension` 扩展跨 Version embedding 复用，避免重复计算。

### 重建原则

以下情况应主动重建：

1. Embedding model 发生变化。
2. Embedding dimension 发生变化。
3. pgvector 数据丢失或需要恢复。
4. Vector index status 为 `failed`。
5. 修改 chunking 参数导致 Chunk 集合发生变化。

重建接口：

```http
POST /api/v1/knowledge/{knowledge_base_id}/documents/{document_id}/versions/{version_id}/vector-index
```

## 4. 配置

真实 Vector 闭环要求：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_API_KEY=your-key
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

`EMBEDDING_DIMENSION` 必须同时匹配真实 Provider 返回值和 migration 0010 的 vector column dimension。

## 5. 本地验证

### Contract

```powershell
cd backend
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py tests/test_knowledge_vector_indexing.py tests/test_vector_knowledge_retrieval.py
```

### pgvector

```powershell
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pgvector_validation.ps1
```

### Embedding Provider

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_embedding_provider_validation.ps1
```

真实 Provider 未配置时，probe 应跳过；不能把 skip 当作真实 Provider 通过。

### 全量 Backend

```powershell
cd backend
uv run pytest -q
```

### Frontend

```powershell
cd frontend
npm test
npm run build
```

## 6. 质量评估

现有 Evaluation Dataset 用于比较：

- lexical-v2
- vector
- 后续 hybrid

至少记录：

- Recall@K
- Precision@K
- MRR
- 平均 latency
- provider error rate

Vector 与 lexical 使用相同 Knowledge Base scope、相同 top-k 与相同 Evaluation Dataset，避免数据集或权限边界造成不可比结果。

## 7. 失败与降级规则

| 场景 | 默认行为 | 显式降级 |
|---|---|---|
| `VECTOR_PROVIDER=none` | Vector 返回 503 | `fallback_to_lexical=true` 时 lexical |
| Embedding 未配置 | Vector 返回 503 | `fallback_to_lexical=true` 时 lexical |
| Embedding 请求失败 | Vector 返回 503 | `fallback_to_lexical=true` 时 lexical |
| pgvector 查询失败 | Vector 返回 503 | `fallback_to_lexical=true` 时 lexical |
| Vector dimension mismatch | Vector 返回 503 | `fallback_to_lexical=true` 时 lexical |
| 无命中 | 返回空结果 | 不自动扩大权限或范围 |

核心原则：**失败不能扩大检索权限，也不能静默改变 retrieval semantics。**

## 8. 当前限制

- 当前真实 Vector Provider 只实现 PostgreSQL + pgvector。
- 当前没有自动后台索引队列，重建通过 API / 本地脚本触发。
- 当前跨 Version 的 content-hash embedding 复用尚未实现。
- Hybrid retrieval 尚未进入实现阶段。
- 当前质量门禁仍在本地执行，不以 GitHub Actions 结果作为本阶段验收依据。
