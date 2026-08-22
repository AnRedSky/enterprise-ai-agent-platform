# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新产品基线：Phase 2.1 Enterprise Organization & Access Governance 已完成最终联合验收并正式关闭。
- 开发原则：所有任务直接基于最新 `main`；禁止创建功能分支、临时分支或长期分支。
- 当前开发阶段：**Phase 1.9 已完成 / 正式关闭；Phase 2.1 已完成 / 正式关闭；Phase 2.2 进行中，2.2-A Contract 已形成，2.2-B 已通过本地 Gate，当前执行 2.2-C Real Provider Quality Gate。**
- 产品能力基线：`docs/PRODUCT_CAPABILITY_BASELINE.md`
- 产品与功能开发对比矩阵：`docs/PRODUCT_DEVELOPMENT_MATRIX.md`
- 产品整体路线：`docs/PRODUCT_ROADMAP.md`

## 2. Phase 2.1 最终联合验收证据

### Frontend Regression / Build

```text
16 test files passed
69 tests passed
Production build passed
[PASS] Frontend regression gate completed.
```

### Backend Regression

```text
275 passed, 30 deselected in 6.92s
```

### Real API

```text
[1/2] Prepare real API test context
Real API context prepared: .real_api_context_39ad1c1c1d55
[2/2] Execute all real HTTP API tests
30 passed in 39.91s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### Browser E2E

```text
scripts/test/e2e/02_run_organization_e2e.ps1
3 passed (14.2s)
[PASS] Phase 2.1-F organization browser E2E contract completed.

npx playwright test tests/e2e/organization-management.spec.ts --project="Desktop Chrome"
3 passed (12.8s)
```

### Phase 2.1 结论

以上证据共同满足 Phase 2.1 Definition of Done：Contract、Migration、Backend、Real API、Frontend、Browser E2E、成员生命周期、权限边界和 Audit 均已验证。

**Phase 2.1 正式关闭。**

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| Phase 1.9 | 已完成 / 正式关闭 | Runtime Reliability / Production Hardening 全部 Acceptance Gate 通过 |
| **Phase 2.1** | **已完成 / 正式关闭** | Enterprise Organization & Access Governance；A～F-C 全部 Gate 与最终联合验收通过 |
| **Phase 2.2** | **进行中** | Retrieval Production Quality；2.2-A 已形成，2.2-B 本地 Gate 已通过，当前为 2.2-C Real Provider Quality Gate |
| Phase 2.3～2.8 | 路线候选 | Model Governance、Durable Scheduler、Advanced Workflow、Event Infrastructure、Multi-Agent、Agent Marketplace |

## 4. Phase 2.2 当前任务

### 2.2-A Product / Retrieval Quality Contract — **已形成**

已明确 Provider / Dataset / Corpus 边界、Recall@K / Precision@K / MRR、Citation correctness、latency、provider error rate、baseline regression 与 failure/fallback semantics。真实 Provider Quality Gate 尚未通过。

### 2.2-B Evaluation Dataset / Runner — **本地 Gate 已通过**

本次实现直接复用现有 `retrieval_evaluation.py`、`knowledge_retrieval_dataset.jsonl`、PostgreSQL/pgvector fixture 与 baseline：

- 新增严格 JSONL Dataset Loader：校验 JSON、case id、query、relevant chunk IDs、重复 case ID、空数据集。
- Runner 改为通过 Dataset Loader 消费现有评测数据，不再重复解析 Dataset。
- Runner 输出 dataset schema version、case 级 ranking / latency / error、聚合 Recall@K / Precision@K / MRR / error rate / average latency。
- Runner 仍通过真实 PostgreSQL/pgvector 执行 Retrieval；评测 JSONL 仅是评测输入，不是生产 Retrieval 数据源。
- Runner 修正 `backend/scripts/evaluation/knowledge` 到 `backend` 的路径解析，并保证 evaluation fixture cleanup 参数正确。

开发者本地实际证据：

```text
Dataset Loader: 4 passed
Retrieval evaluation + Dataset: 10 passed
Backend regression: 279 passed, 30 deselected
Migration head: 0023_organization_membership
Real API: 30 passed
2.2-B runner --k 3: 5/5 cases successful, error_rate=0, recall@3=1.0, precision@3=0.466667, MRR=0.9, quality_gate=passed
```

### 2.2-C Real Provider Quality Gate — **实现完成，待本地 Gate**

新增真实 Provider evaluation runner：

- 复用 `OpenAICompatibleEmbeddingProvider`，明确要求 `EMBEDDING_PROVIDER=openai-compatible`。
- 复用现有 PostgreSQL/pgvector fixture 与 `PgVectorRetrievalProvider`。
- 不提供静默 lexical fallback；`fallback_used=false` 与 `fallback_count=0` 明确进入报告。
- Provider failure 保留在 case observation / error 中，并使 Gate failure。
- 输出 provider、model、embedding dimension、dataset version、retrieval mode、top-k、latency、error、fallback 与 baseline status。
- 新增 real baseline helper，支持显式 `--freeze-baseline`；第一次冻结不会被错误标记为 Passed。
- 后续执行比较 provider/model/dimension/dataset/retrieval mode/top-k identity，以及 Recall@K / MRR 和 provider error rate。
- 不提交真实 Provider API key，也不预置虚假 baseline 指标。

当前未执行真实 Provider Gate，因此 **不得标记 2.2-C Passed**。

下一步：

1. 使用未提交的 `backend/.env` 配置真实 OpenAI-compatible Embedding Provider 与 pgvector。
2. 执行 `run_knowledge_retrieval_real_provider.py --k 3 --freeze-baseline` 并人工审阅真实结果。
3. 冻结 baseline 后重新执行相同 runner，确认 regression Gate。
4. 若出现真实 Provider failure / dimension mismatch / quality regression，先记录 `docs/04-errors/`，再修复后重新 Gate。

## 5. 维护规则

后续任何功能完成、延期、阻塞、范围变化或新的工程错误，都必须同步：

- `docs/PROJECT_STATUS.md`
- 对应 `docs/02-phases/PHASE_x_y.md`
- 对应 `docs/03-acceptance/PHASE_x_y_ACCEPTANCE.md`
- 已分析完成的工程错误同步 `docs/04-errors/`

同一任务的多份文档变更应作为一个文档变更集一次性提交，避免每个文档形成独立中间提交。
