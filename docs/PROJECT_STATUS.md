# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：当前定义范围已完成并有 Real API evidence。
- 2.2-E Model Provider / Model Profile Governance Foundation：E-1、E-2 已完成当前代码实现；E-2 cross-dimension 本地 evidence 已由开发者实际执行通过，当前处于 E-3 Frontend Provider/Profile Management 修复与验收阶段。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建功能分支。当前远端 main 最新基线为 `ba830da2a4db33154ffdc5c24bc9d808b4858c8e`，包含 Model Provider UI 测试中的 vue-router mock 修复。

## E-2 实际验证证据

开发者本地实际执行并反馈：

```text
Cross-dimension targeted tests: 13 passed
Migration head: 0027_retrieval_evaluation_vector_space
Backend regression gate: 323 passed, 31 deselected
Real HTTP API: 31 passed
Standalone Real API Gate: 31 passed
Governed E-2 smoke: status=passed
  Profile A: nomic-embed-text:latest / 768
  Profile B: qwen3-embedding:0.6b / 1024
  retrieval_mode=real-provider-pgvector
  retrieval_execution_path=runtime-service
  fallback_count=0 / fallback_used=false
  Profile B regression quality_gate=failed because governed identity changed (expected)
  Profile B metrics: recall@3=1.0, precision@3=0.466667, mrr=1.0
```

这里的 `Profile B quality_gate=failed` 不是测试失败，而是本次 smoke 对 baseline identity change 的预期断言：model、dimension、model_profile_id 改变时必须拒绝复用 Profile A baseline。Smoke 顶层 `status=passed`，说明该治理回归规则被正确触发。

Real API 与 Backend Gate 均保持独立；Frontend / Browser 的新一轮本地 Gate 结果以开发者实际执行为准。

## E-2 Contract 结论

```text
Production Vector Space
  knowledge_chunks.embedding -> fixed configured production dimension (current 768)

Evaluation Vector Space
  retrieval_evaluation_vectors.embedding -> variable pgvector vector
  + embedding_dimension -> actual governed Profile dimension
  + knowledge_base_id -> evaluation scope
```

不同 Embedding Profile 不要求相同 dimension；每个 Profile 必须严格匹配自己的实际 embedding dimension，并在 Evaluation Vector Space 内按 dimension 隔离。生产 `knowledge_chunks` 不修改、不降维、不截断。

## 已完成修复

- Migration `0027_retrieval_evaluation_vector_space` 已验证到 head。
- Evaluation Vector Space 与生产 fixed-dimension `knowledge_chunks` 分离。
- Governed smoke 采用同一 async event loop 完成 DB fixture 创建、runner 前后清理，避免跨 event loop 复用异步数据库资源。
- E-2 smoke 不下载模型；本次使用本地已安装 `nomic-embed-text:latest` 与 `qwen3-embedding:0.6b`。
- Secret 未进入 evaluation report / trace / audit / Git。
- E-3 targeted Vitest 的 vue-router 注入问题已在 `ba830da` 修复。
- E-3 Frontend production build 暴露的 Element Plus `el-table` 默认 `DefaultRow` 与 `ModelProfile` handler 参数类型冲突已在本次修复中处理：表格 row 入口先以 `unknown` 接收，再在边界函数中转换为领域类型，避免模板类型推断污染业务 handler。

## E-3 当前任务

当前 E-3 已完成代码实现与测试阻塞修复：

1. organization-scoped Model Provider/Profile API types 与 client。
2. Provider/Profile 管理 UI，支持 CRUD、enabled/default、Embedding dimension 展示与 Chat dimension 边界。
3. 从 Organization detail 进入 Provider/Profile 管理页。
4. Frontend Vitest API/UI tests。
5. 修复测试环境缺少 vue-router 注入导致的 `route.params` 崩溃。
6. 修复 production build 中 Element Plus `DefaultRow` 与 `ModelProfile` handler 的 TypeScript 类型冲突。

**注意：本次代码修复尚未由本助手在开发者本地执行 Frontend Regression Gate 验证，因此不得标记 E-3 Passed。**

## 下一步

1. 开发者执行 E-3 targeted Vitest，确认 Model Provider/Profile API/UI tests 保持通过。
2. 执行 Frontend Regression Gate（test → production build），重点确认 `vue-tsc` 与 Vite production build 均通过。
3. 如 UI 纳入 Browser 验收，再执行独立 Browser E2E；不得把 Frontend Gate 与 Backend Gate 合并。
4. E-3 Gate 通过后，进入 2.2-E-4 Acceptance，汇总 Runtime / Evaluation / Audit / Trace 与 Frontend evidence。
5. E-4 前先确认 Acceptance 文档中的实际证据与本轮执行结果一致，不得使用未重新执行的旧结果冒充当前验收证据。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码；UI 测试中的模型字符串仅作为 fixture contract。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
- PowerShell `<PROFILE_UUID>` 占位符误用已记录在 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-placeholder-command.md`；后续优先使用自动化 smoke script。
