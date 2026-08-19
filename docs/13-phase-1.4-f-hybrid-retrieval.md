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

## 5. F-03 真实 Hybrid Quality Evaluation

F-03 已完成本地质量评测：

- 评测输入为 Evaluation Fixture；实际 ranking 来自 FastAPI Retrieval API。
- 数据源为真实 PostgreSQL/pgvector Knowledge Chunk；JSON fixture 不是 Retrieval 结果源。
- `k=3`，5 个 evaluation cases，`EMBEDDING_PROVIDER=mock` 仅替代 embedding 生成。
- lexical-v2：Recall@3=1.0、Precision@3=1.0、MRR=1.0、error_rate=0。
- vector：Recall@3=1.0、Precision@3=0.466667、MRR=1.0、error_rate=0。
- hybrid：Recall@3=1.0、Precision@3=0.466667、MRR=1.0、error_rate=0。
- Hybrid quality gate：passed。
- Full backend regression：148 passed，86 warnings。

本轮没有通过修改 baseline 或隐藏错误来获得通过结果。

## 6. G-01 Retrieval Debug

G-01 已实现：

### Backend

Hybrid API response 新增：

```json
{
  "retrieval_sources": ["lexical", "vector"],
  "hybrid_score_breakdown": {
    "lexical_score": 0.9,
    "vector_score": 0.75,
    "lexical_weight": 0.4,
    "vector_weight": 0.6,
    "fused_score": 0.81,
    "support": ["lexical", "vector"]
  }
}
```

该 breakdown 由真实 Hybrid fusion service 生成，前端不重新计算业务分数。

### Frontend

Knowledge Retrieval Debug 已支持：

- Lexical v2 / Vector / Hybrid 模式切换；
- Hybrid lexical / vector 权重输入；
- 来源拆解；
- lexical score；
- vector score；
- fused score；
- citation / source URI / content。

新增本地验证入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_g_01_retrieval_debug_validation.ps1
```

该脚本执行 Backend hybrid contract、Frontend Retrieval Debug Vitest 和 frontend production build；不触发 GitHub Actions。

## 7. 边界

本阶段不做：

- 模型型 Reranker；
- JSONL 作为线上检索结果源；
- 新增独立 Vector DB；
- 修改已有 Knowledge RBAC 规则；
- Runtime trace 深度关联。

后续：

- G-02：Runtime execution / trace 与 Retrieval Debug 关联；
- 后续再评估真实 Embedding Provider 的语义质量与 reranker。

## 8. 测试

### Backend G-01

```powershell
cd backend
uv run pytest -q tests/test_hybrid_knowledge_retrieval.py tests/test_hybrid_retrieval_api_contract.py tests/test_hybrid_knowledge_retrieval_service.py
```

### Frontend G-01

```powershell
cd frontend
npm test -- --run tests/views/knowledge/KnowledgeWorkbench.test.ts
npm run build
```

### 一键本地验证

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_g_01_retrieval_debug_validation.ps1
```

测试结果只能记录开发者实际执行并反馈的结果，不预填“通过”。

## 9. 当前状态

| ID | 任务 | 状态 | 责任角色 | 目标时间 |
|---|---|---|---|---|
| 1.4-F-01 | Hybrid Retrieval Contract / score fusion | 已完成本地回归 | Backend / Knowledge | 2026-08-20 |
| 1.4-F-02 | lexical-v2 + vector 真实服务编排、`mode=hybrid` API、Citation 闭环 | 已实现并完成真实 DB loop 验收 | Backend / Knowledge | 2026-08-20 |
| 1.4-F-03 | Hybrid Evaluation Dataset、权重评测与 quality gate | 已完成，本地质量门禁通过 | Backend / QA | 2026-08-21 |
| 1.4-G-01 | Retrieval Debug hybrid 来源/分数展示 | 已实现，等待开发者执行本地验证 | Frontend / Backend | 2026-08-22 |
| 1.4-G-02 | Runtime execution / trace 与 Retrieval Debug 关联 | 下一任务 | Backend / Frontend | 2026-08-24 |

真实 Embedding Provider、endpoint、API key 和数据库凭据仍只允许存在本地未提交 `backend/.env`。
