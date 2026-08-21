# Phase 1.4 — Acceptance

## 1. 验收范围

Knowledge Registry、Document / Version / Chunk ingestion、Runtime Knowledge integration、Retrieval、Citation、Knowledge / Retrieval Debug 前端，以及 Retrieval Provider validation。

## 2. 历史验收记录迁移

以下历史验收记录已经逐份读取并归并：

- `PHASE_1_4_D_ACCEPTANCE.md`：Runtime + Knowledge 联调门禁，链路为 Auth → Knowledge Base → Document → Version → Ingest → AgentVersion Knowledge Config → Runtime Chat → Citation → Audit / Observability。
- `PHASE_1_4_FG_ACCEPTANCE.md`：Vue Knowledge / Retrieval Debug，包括 Knowledge 工作台、query/top-k/scope、loading/error/empty、Citation Detail / Source URI。

## 3. 历史 E/F/G 验证证据

### 3.1 Retrieval baseline

历史 E baseline 要求 ranking 来自生产 `lexical-v2` scoring，Evaluation Dataset 只定义 query/relevant chunk，不参与 ranking；指标为 Recall@K / Precision@K / MRR，并要求稳定排序。

### 3.2 Vector / pgvector

历史记录确认已经形成 provider-neutral contract、PostgreSQL + pgvector adapter、Vector indexing service、vector index status 和 `mode=vector` Retrieval API。`fallback_to_lexical` 必须显式开启，默认不能静默把 Vector 失败伪装成 lexical 成功。

### 3.3 Mock Embedding

Mock 仅用于 deterministic pipeline validation。历史 2026-08-19 记录了中文短查询导致 mock Quality Gate 失败：Recall@K=0.6、Precision@K=0.266667、MRR=0.5、error_rate=0；根因被定位为中文 token 特征构造不足，随后通过中文 bigram 特征修复。该记录只能证明 fixture 修复过程，不能证明真实 Embedding 语义质量。

同日另一历史记录显示 retrieval evaluation runner 曾因原生 SQL fixture 未显式提供 `created_at` / `updated_at` 而在 `knowledge_bases` 创建阶段失败；修复后要求重新执行 runner 和 Quality Gate，旧文档没有把未执行结果写成通过。

### 3.4 Hybrid Retrieval

历史 F-03 记录：5 个 evaluation cases、k=3，lexical Recall@3=1.0 / Precision@3=1.0 / MRR=1.0 / error_rate=0；vector Recall@3=1.0 / Precision@3=0.466667 / MRR=1.0 / error_rate=0；hybrid Recall@3=1.0 / Precision@3=0.466667 / MRR=1.0 / error_rate=0；Hybrid quality gate=passed。历史记录同时报告一次 Full backend regression 为 148 passed、86 warnings。该数字作为历史证据保留，不覆盖当前项目状态中的其他回归结果。

### 3.5 Runtime / Knowledge 联调

历史 D acceptance 固定 Auth → Knowledge Base → Document → Version → Ingest → AgentVersion Knowledge Config → Runtime Chat → Citation → Audit / Observability 链路，并要求 `uv sync`、Alembic upgrade、Backend pytest、Runtime Knowledge scenario、Frontend npm test、Frontend build。

### 3.6 Vue Knowledge / Retrieval Debug

历史 F/G acceptance 固定 Knowledge Base → Document → Version → Chunk 工作台和 Retrieval Debug 的 query/top-k/scope、loading/error/empty、来源、Score、Citation、Source URI，以及浏览器操作路径。

## 4. Acceptance Gate

- `uv sync`
- `uv run alembic upgrade head`
- `uv run pytest -q`
- Runtime Knowledge scenario
- `npm test`
- `npm run build`
- Retrieval / Provider validation scenarios

上述命令是验收门禁定义，不代表本次文档迁移重新执行过这些测试。

## 5. 核心 Contract

Version 必须有 ingestion lifecycle；Chunk 必须关联 `document_version_id`，`chunk_index` 在 Version 内唯一且从 0 递增，`char_start / char_end` 可追溯清洗文本，`content_hash` 稳定；重复 ingestion 不产生重复 Chunk；Owner / RBAC 隔离必须成立。

Retrieval 结果必须能够追溯 source document / chunk、score、citation 和 source URI。

## 6. 当前结论规则

本次 Docs Governance Refactor 不重新执行历史 Phase 1.4 测试，因此不新增“当前通过”结论。历史测试结果仅作为历史证据保留；当前状态以 `PROJECT_STATUS.md` 和本 Acceptance 中已明确记录的实际反馈为准。

## 7. 迁移来源完整清单

- `11-phase-1.4-knowledge-rag-plan.md`
- `12-phase-1.4-e-retrieval-baseline.md`
- `12-phase-1.4-e-vector-retrieval-provider.md`
- `13-phase-1.4-e-vector-retrieval-validation.md`
- `13-phase-1.4-f-hybrid-retrieval.md`
- `14-phase-1.4-e-provider-validation-checkpoint.md`
- `15-phase-1.4-e-mock-embedding-validation.md`
- `phase-1.4-e-retrieval-evaluation-mock-embedding-fix-2026-08-19.md`
- `phase-1.4-e-retrieval-evaluation-runner-fix-2026-08-19.md`
- `PHASE_1_4_D_ACCEPTANCE.md`
- `PHASE_1_4_FG_ACCEPTANCE.md`
