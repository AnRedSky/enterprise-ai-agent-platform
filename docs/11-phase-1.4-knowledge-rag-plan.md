# Phase 1.4：Knowledge / RAG 功能闭环规划与执行基线

> 本文是 Phase 1.4 的开发基线。所有开发直接提交 `main`，不创建新的功能分支。固定开发顺序以 `docs/DEVELOPMENT.md` 为准。当前项目处于本地开发 / 测试阶段，暂不执行 GitHub Actions CI；质量门禁由本地 `uv run` / `npm` 测试与手工验收脚本承担。

## 1. 阶段目标

Phase 1.4 聚焦 Knowledge / RAG，目标不是一次性接入某个具体向量数据库，而是先建立与现有 Agent Runtime、RBAC、Observability 解耦的知识领域边界，并形成可验收闭环：

```text
Knowledge Base → Document → Version → Chunk → Index / Retrieval contract → Context Builder → Agent Runtime → Citation / Trace
```

## 2. 后端并行开发顺序

### 1.4-A Knowledge Registry
- [x] KnowledgeBase 元数据、Owner、状态
- [x] Document 元数据、来源、状态、版本关联
- [x] RBAC owner isolation
- [x] CRUD API 与分页
- [x] Alembic migration `0007_knowledge_registry`
- [x] Backend pytest：API contract 回归测试已提交
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_registry_scenario.ps1`
- [x] 本地手工验收：Knowledge Registry 场景已通过（CRUD、Version、分页、删除、Owner/RBAC）

### 1.4-B Document ingestion
- [x] 文档内容抽象与 parser/cleaner contract
- [x] 清洗、确定性分块策略 contract
- [x] Chunk 持久化：migration `0008_knowledge_ingestion`
- [x] 增量重新摄取：同一 Version 先删除旧 Chunk 再生成新 Chunk
- [x] ingestion 状态机：`pending → processing → ready / failed`
- [x] Chunk 与 Document Version 可追溯
- [x] Backend pytest：chunk contract / API contract
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_ingestion_scenario.ps1`
- [x] 本地手工验收：Version → Ingest → Chunks → Re-ingest 已通过

### 1.4-C Retrieval contract
- [x] Embedding provider interface
- [x] Retriever interface
- [x] Reranker interface（先定义 contract）
- [x] Provider-neutral retrieval result
- [x] source document / chunk / relevance score / citation
- [x] 第一版 provider-neutral lexical retrieval 实现，不绑定具体向量数据库
- [x] Knowledge Base owner isolation 在检索查询阶段执行
- [x] 独立手工验收脚本：`backend/scripts/run_knowledge_retrieval_scenario.ps1`
- [x] 本地 pytest + Retrieval 手工验收已通过

### 1.4-D Runtime integration
- [x] AgentVersion 可声明 Knowledge 配置（`knowledge_base_ids` + `top_k`）
- [x] Runtime Context Assembly 接入检索结果
- [x] 保持 `execution_id / trace_id / agent_version` 链路
- [x] 权限过滤必须发生在检索结果进入模型上下文之前
- [x] 引用结果通过 SSE start/done 事件向调用方返回
- [x] Retrieval span 写入 Observability
- [x] Runtime + Knowledge 联调手工验收
- [x] 前后端第一轮回归

### 1.4-E Knowledge / Retrieval 生产化深化
- [x] 检索策略升级为 deterministic `lexical-v2`
- [x] 中文短语增加序列/二元 token，避免连续中文文本无法命中
- [x] `min_score` 阈值控制
- [x] 可选重复 Chunk 去重
- [x] 返回 `matched_terms` 与 `retrieval_mode`
- [x] 候选扫描设置上限并保持稳定排序
- [x] Retrieval API schema 与前端 API 类型同步升级
- [x] retrieval quality / API contract 单元测试
- [x] 离线 Evaluation Case contract：Recall@K / Precision@K / MRR
- [x] Evaluation Dataset 与 lexical-v2 baseline
- [x] Retrieval baseline quality gate
- [x] OpenAI-compatible Embedding Provider adapter、contract tests、真实 probe
- [x] provider-neutral Vector Retrieval contract 与 deterministic in-memory adapter
- [x] PostgreSQL + pgvector adapter、migration 0010/0011、indexing service
- [x] vector retrieval API：`mode=vector`，保留显式 lexical fallback
- [x] mock Embedding + PostgreSQL/pgvector deterministic retrieval quality gate
- [x] 本地 Provider Validation 已通过：Recall@3=1.0、Precision@3=0.466667、MRR=0.9、error_rate=0、quality gate=passed
- [x] 评估结果直接来自 PostgreSQL/pgvector `knowledge_chunks`，JSON fixture 仅作为测试数据输入，不作为检索结果数据源
- [x] `EMBEDDING_PROVIDER=mock` 可用于真实 PostgreSQL/pgvector retrieval loop；mock 仅替代 embedding 生成
- [ ] 使用真实 Embedding Provider 完成 endpoint / model / dimension / error boundary 联调
- [ ] 使用真实 Embedding Provider 完成 5 条 Dataset 的真实语义质量对比

> 说明：由于当前开发环境无法获得真实 Embedding 模型，mock Embedding 只证明 deterministic indexing / vector retrieval pipeline，不证明真实模型语义质量。

## 3. 前端并行开发顺序

### 1.4-F Knowledge 管理端
- [x] 独立 `src/views/knowledge/index.vue + components/KnowledgeWorkbench.vue`
- [x] Knowledge Base 列表 / 创建 / 状态展示
- [x] Document 列表 / 创建 / 删除
- [x] Document Version 展示 / 创建
- [x] Chunk 查看
- [x] ingestion 状态与 Ingest 操作
- [x] 错误、空状态基础处理
- [x] 独立 `tests/views/knowledge/KnowledgeWorkbench.test.ts`

### 1.4-G Retrieval / Debug
- [x] Retrieval 调试入口
- [x] query / top-k / Knowledge Base 过滤
- [x] source document / score / citation / content 展示
- [x] 与 Retrieval API 的 `retrieval_mode / matched_terms / min_score` contract 对齐
- [x] G-01：Hybrid retrieval 来源与 lexical/vector/fused score breakdown 展示
- [x] G-02：Runtime execution / trace 与 Retrieval Debug 关联

## 4. Phase 1.4-F Hybrid Retrieval

### 4.1 F-01：Contract / score fusion

已实现并直接提交 `main`：

- `backend/app/services/hybrid_knowledge_retrieval.py`
- `backend/tests/test_hybrid_knowledge_retrieval.py`
- `docs/13-phase-1.4-f-hybrid-retrieval.md`

第一版只建立 provider-neutral score fusion，不直接绑定 pgvector SQL，也不引入 reranker 模型：

```text
lexical-v2 candidates ──┐
                        ├─ weighted fusion → stable hybrid ranking
vector candidates ──────┘
```

默认 lexical / vector 权重均为 `0.5`，分数均假定已经归一化到 `0..1`。相同 chunk 的单路重复候选取最高分；只命中单一路的候选按另一侧 0 分计算但不人为降权；多信号候选优先，同层按 score 降序、chunk_id 升序稳定排序。

### 4.2 F-02：真实数据库服务编排与 Citation 闭环

已实现并直接提交 `main`：

- `KnowledgeRetrievalService`：真实 PostgreSQL Knowledge Chunk lexical retrieval
- `VectorKnowledgeRetrievalService`：Embedding + PostgreSQL/pgvector retrieval
- `HybridKnowledgeRetrievalService`：两路真实 service orchestration + provider-neutral fusion
- `POST /api/v1/knowledge/retrieve`：`mode=hybrid`
- Citation / source hydration：从数据库中的 Document / Version / Chunk 真实回填
- `backend/scripts/run_phase_1_4_f_retrieval_db_loop.py`：真实数据库闭环验证
- `backend/scripts/run_phase_1_4_f_retrieval_db_loop.ps1`：本地手工测试入口

真实链路：

```text
Retrieval API
 ↓
HybridKnowledgeRetrievalService
 ├─ lexical-v2 → PostgreSQL knowledge_document_chunks
 └─ vector → Embedding Provider → PostgreSQL/pgvector knowledge_chunks
 ↓
HybridRetrievalService.fuse()
 ↓
Document / Version / Chunk hydration
 ↓
Citation / content / source_uri
 ↓
API response
```

本地无真实 Embedding 模型时允许 `EMBEDDING_PROVIDER=mock`，但 SQL、pgvector、ingestion、RBAC、API、fusion、citation 等其余链路仍走真实实现；不得用 JSON/JSONL 检索结果替代数据库。

### 4.3 F-03

- [x] Hybrid Evaluation Dataset + Recall@K / Precision@K / MRR + 权重质量门禁
- [x] 本地真实 PostgreSQL/pgvector + FastAPI Retrieval API 质量评测通过
- [x] 5 cases、k=3：lexical Recall@3=1.0 / Precision@3=1.0 / MRR=1.0；vector Recall@3=1.0 / Precision@3=0.466667 / MRR=1.0；hybrid Recall@3=1.0 / Precision@3=0.466667 / MRR=1.0
- [x] error_rate=0，Hybrid 质量门禁通过
- [x] 全量 Backend regression：152 passed，0 warnings

### 4.4 G-01 / G-02

- [x] G-01：Retrieval Debug 展示 lexical/vector/hybrid 来源与 score 拆解；后端返回真实 breakdown，前端直接展示，不重新计算业务分数
- [x] G-02：Runtime execution / trace 与 Retrieval Debug 关联；后端 runtime trace、RBAC、metadata contract 与前端 timeline 展示已完成
- [x] G-02 本地 Backend pytest：152 passed，0 warnings
- [x] G-02 数据库 migration：`0012_execution_event_metadata`，`alembic current` 为 head

## 5. 联调顺序

每个小版本必须按以下顺序推进：

1. Backend contract + migration + pytest
2. Frontend API types + Vitest
3. Frontend UI
4. API scenario / 手工验收脚本
5. Runtime integration
6. 前后端联调
7. `backend pytest` + `frontend npm test` + `frontend npm run build`
8. 更新验收文档后提交 `main`

当前阶段测试由本地开发环境执行，不执行 GitHub Actions CI。

## 6. 当前状态

**Phase 1.4-A / B / C / D / E / F / G 已完成当前已定义范围的本地开发与回归验收。G-02 已完成，Backend 当前基线为 152 passed、0 warnings，PostgreSQL migration `0012_execution_event_metadata` 已处于 head。**

下一任务：**进入 Phase 1.5 Workflow / Governance 前，先建立并提交明确的 Phase 1.5 开发基线与任务拆解；在基线确认后严格按 Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归顺序推进。**

## 7. 暂不在第一轮实现

- 强绑定 Milvus / Elasticsearch 等具体基础设施
- 自动 OCR 全套能力
- 复杂 reranker 模型部署
- Knowledge 多租户高级策略
- 生产级异步 MQ / 分布式 ingestion

这些能力在第一轮 contract 闭环完成后再逐步实现，避免架构过早绑定。
