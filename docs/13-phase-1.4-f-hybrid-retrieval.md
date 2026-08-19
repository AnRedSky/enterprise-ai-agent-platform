# Phase 1.4-F：Hybrid Retrieval

> 本阶段继续遵循 `docs/DEVELOPMENT.md`：代码直接进入 `main`，测试由开发者本地手动执行；不使用 GitHub Actions workflow 作为测试或验收依据。

## 1. 目标

在已经稳定的 `lexical-v2` 与 `vector` retrieval contract 之上，建立真实数据库驱动的 Hybrid Retrieval：

```text
Query
 ├─ lexical-v2 ──┐
 │               ├─ score fusion ──> hybrid ranking
 └─ vector ──────┘
                  ↓
          PostgreSQL / pgvector
```

Hybrid Retrieval 必须沿用现有 Knowledge Base / Document / Version / Chunk 数据模型和 RBAC，不允许通过 JSONL 结果文件充当线上检索数据源。

## 2. F-01 Contract

`HybridRetrievalService` 提供 provider-neutral score fusion：

- `HybridCandidate`：chunk、0..1 score、来源及业务 payload。
- `HybridRetrievalConfig`：控制 lexical / vector 权重。
- 同一 chunk 在单一来源重复出现时取最高 score。
- 同时命中 lexical + vector 时执行配置权重融合。
- 仅命中单一来源时保留该来源的归一化原始 score，不因另一来源缺失而降权。
- 多信号候选优先于单信号候选；同一支持层内按 score 降序、`chunk_id` 升序稳定排序。
- 第一版不引入模型型 reranker。

## 3. F-02 实现范围

已实现真实服务编排：

1. `KnowledgeRetrievalService` 执行 lexical-v2 数据库检索；
2. `VectorKnowledgeRetrievalService` 执行 Embedding + PostgreSQL/pgvector 检索；
3. 两路结果经过现有 RBAC / Knowledge Base scope / Document scope；
4. `HybridKnowledgeRetrievalService` 将两路结果转换为 `HybridCandidate` 后融合；
5. API `/api/v1/knowledge/retrieve` 支持 `mode=hybrid`；
6. API 返回 `retrieval_mode=hybrid` 和 `retrieval_sources`，保留 citation/content/source URI；
7. `min_score` 在融合后执行；
8. lexical/vector 权重由 API contract 明确传入，默认 `0.5 / 0.5`。
9. `EMBEDDING_PROVIDER=mock` 可用于本地真实 PostgreSQL/pgvector 闭环验证；mock 只替代 embedding 生成，不替代 SQL、索引、RBAC、Hybrid、API 或 Citation hydration。

线上检索链路：

```text
API
 ↓
HybridKnowledgeRetrievalService
 ├─ KnowledgeRetrievalService
 │    └─ PostgreSQL knowledge_document_chunks
 └─ VectorKnowledgeRetrievalService
      ├─ Embedding Provider
      └─ PostgreSQL / pgvector knowledge_chunks
 ↓
HybridRetrievalService.fuse()
 ↓
Citation / source hydration
 ↓
API Response
```

## 4. F-02 真实数据库闭环验收

新增本地手工验收：

```text
backend/scripts/run_phase_1_4_f_retrieval_db_loop.py
backend/scripts/run_phase_1_4_f_retrieval_db_loop.ps1
```

该验收脚本不是 JSONL evaluation runner，而是直接走真实应用链路：

```text
PostgreSQL fixture
 → KnowledgeIngestionService
 → PostgreSQL knowledge_document_chunks
 → EmbeddingProvider（mock 或真实 OpenAI-compatible）
 → PostgreSQL/pgvector knowledge_chunks
 → FastAPI /api/v1/knowledge/retrieve
 → lexical + vector
 → Hybrid fusion
 → Citation hydration
 → API response
```

验收脚本会创建临时 Knowledge Base / Document / Version，完成 ingestion 与 vector indexing，然后通过 FastAPI ASGI 路由调用 Retrieval API；结束后删除 fixture 及对应 pgvector 记录。

### 本地配置

若没有真实 Embedding Provider，可使用：

```text
EMBEDDING_PROVIDER=mock
VECTOR_PROVIDER=pgvector
```

此模式只证明真实 PostgreSQL/pgvector 检索链路和应用业务闭环，不证明真实模型语义质量。配置真实 Provider 时：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=...
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=...
VECTOR_PROVIDER=pgvector
```

密钥只允许存在未提交的 `backend/.env`。

## 5. 边界

本阶段不做：

- 模型型 Reranker；
- JSONL 作为线上检索结果源；
- 新增独立 Vector DB；
- 修改已有 Knowledge RBAC 规则；
- 前端 Retrieval Debug UI 的 hybrid 展示。

后续：

- F-03：Hybrid Evaluation Dataset + Recall@K / Precision@K / MRR + 权重质量门禁；
- G-01：Retrieval Debug 展示 lexical/vector 来源与融合分数；
- G-02：Runtime execution / trace 与 Retrieval Debug 关联。

## 6. 测试

### 单元 / Contract

```powershell
cd backend
uv run pytest -q tests/test_hybrid_knowledge_retrieval.py
uv run pytest -q tests/test_hybrid_knowledge_retrieval_service.py tests/test_hybrid_retrieval_api_contract.py tests/test_vector_knowledge_retrieval.py
```

### 真实数据库闭环

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_f_retrieval_db_loop.ps1
```

脚本只执行本地 `pytest` 和本地 Python/ASGI/数据库验证，不触发 GitHub Actions workflow。

### 真实数据库手工验收重点

1. 启动 PostgreSQL + pgvector。
2. 执行 `uv run alembic upgrade head`。
3. 确认本地 `backend/.env` 已配置 `VECTOR_PROVIDER=pgvector`。
4. 无真实 Embedding Provider 时设置 `EMBEDDING_PROVIDER=mock`；有真实 Provider 时配置 OpenAI-compatible endpoint/model/key。
5. 执行 `run_phase_1_4_f_retrieval_db_loop.ps1`。
6. 验证脚本输出 `source=PostgreSQL/pgvector`、`retrieval_mode=hybrid`、结果包含 `citation` / `content` / `source_document` / `relevance_score`。
7. 对同时命中两路的结果验证 `retrieval_sources` 同时包含 `lexical` 和 `vector`。
8. 使用 `knowledge_base_id` / `document_id` 验证 scope 与 RBAC 仍然有效。
9. 检查临时 fixture 被清理，不留下线上检索 JSON/JSONL 结果文件。

测试结果只能记录开发者实际执行并反馈的结果，不预填“通过”。

## 7. 当前状态

| ID | 任务 | 状态 | 责任角色 | 目标时间 |
|---|---|---|---|---|
| 1.4-F-01 | Hybrid Retrieval Contract / score fusion | 已实现，已完成本地回归 | Backend / Knowledge | 2026-08-20 |
| 1.4-F-02 | lexical-v2 + vector 真实服务编排、`mode=hybrid` API、Citation 闭环 | 已实现，新增真实 PostgreSQL/pgvector 本地闭环验收脚本，等待开发者执行 | Backend / Knowledge | 2026-08-20 |
| 1.4-F-03 | Hybrid Evaluation Dataset、权重评测与 quality gate | 未开始 | Backend / QA | 2026-08-21 |
| 1.4-G-01 | Retrieval Debug hybrid 来源/分数展示 | 未开始 | Frontend | 2026-08-22 |
| 1.4-G-02 | Runtime execution / trace 与 Retrieval Debug 关联 | 未开始 | Backend / Frontend | 2026-08-24 |

真实 Embedding Provider、endpoint、API key 和数据库凭据仍只允许存在本地未提交 `backend/.env`。
