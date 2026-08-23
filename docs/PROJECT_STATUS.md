# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：当前定义范围已完成并有 Real API evidence。
- 2.2-E Model Provider / Model Profile Governance Foundation：E-1、E-2 已完成当前代码实现；E-2 cross-dimension 本地 evidence 已由开发者实际执行通过，当前进入 E-3 Frontend Provider/Profile Management。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建功能分支。当前远端 main 最新基线为 `dc9592493a39ba16f0d054098eb82305c4ac0a57`，包含 governed smoke DB lifecycle 单事件循环修复。

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

Real API 与 Backend Gate 均保持独立；Frontend 尚未执行，本轮不能把 Frontend/Browser 标记为 Passed。

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

## E-3 当前任务

已开始 Frontend Provider/Profile Management：

1. 增加 organization-scoped Model Provider/Profile API types 与 client。
2. 增加 Provider/Profile 管理 UI，支持 CRUD、enabled/default、Embedding dimension 展示与 Chat dimension 边界。
3. 从 Organization detail 进入 Provider/Profile 管理页。
4. 增加 Frontend Vitest API/UI tests。

E-3 当前仅完成代码提交，**未执行本地 Frontend Gate / Browser E2E，禁止标记 Passed**。

## 下一步

1. 开发者执行 E-3 Frontend targeted Vitest。
2. 执行 Frontend Regression Gate（test → production build）。
3. 如 UI 纳入 Browser 验收，再执行独立 Browser E2E；不得把 Frontend Gate 与 Backend Gate 合并。
4. Real API 已验证的 Backend contract 不需要由 Frontend 测试替代；E-3 重点验证 API types/client、权限错误展示、CRUD UI 与 Secret reference 不泄露。
5. E-3 通过后进入 2.2-E-4 Acceptance，完成 Runtime / Evaluation / Audit / Trace 与 Frontend evidence 汇总。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码；UI 测试中的模型字符串仅作为 fixture contract。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
- PowerShell `<PROFILE_UUID>` 占位符误用已记录在 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-placeholder-command.md`；后续优先使用自动化 smoke script。
