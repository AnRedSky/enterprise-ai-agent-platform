# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：进行中。
- 2.2-A Contract：已形成。
- 2.2-B Dataset / Runner：已完成既有交付范围，并已有开发者实际执行验证。
- 2.2-C Real Provider Quality Gate：已通过当前 main 的真实 Provider baseline regression。
- 2.2-D Retrieval Quality Regression / Traceability：当前定义范围已完成并有 Real API evidence。
- 2.2-E Model Provider / Model Profile Governance Foundation：E-1、E-2 已完成当前代码实现；E-2 cross-dimension 本地 evidence 已由开发者实际执行通过；E-3 Frontend Provider/Profile Management 已由开发者实际执行 targeted Vitest 与 Frontend Regression Gate 并通过，当前进入 E-4 Acceptance evidence 汇总阶段。

## 当前 main 基线

开发严格基于最新 `main`，所有修复与开发直接提交 `main`，不创建功能分支。当前远端 main 最新基线为 `0a4462a92f78f19bc9746d1a167add87b062905a`，包含 Model Provider/Profile production build 类型冲突修复。

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

## E-3 实际验证证据

开发者在当前 main `0a4462a` 上实际执行并反馈：

```text
Targeted Vitest:
  tests/api/modelProviders.test.ts + tests/views/ModelProviders.test.ts
  2 test files passed
  6 tests passed

Frontend Regression Gate:
  18 test files passed
  75 tests passed
  production build: passed
  vue-tsc -b: passed
  Vite build: passed
  built in 5.41s

Browser E2E:
  Phase 2.1-F organization browser contract
  3 tests passed
```

Browser E2E 属于既有 Organization governance contract，不作为 Model Provider/Profile 专项 Browser evidence。

## E-3 当前结论

E-3 已完成代码实现、测试阻塞修复，并由开发者本地实际执行 targeted Vitest 与 Frontend Regression Gate 通过，因此 **E-3 Passed**。

此前两个阻塞分别为：

- vue-router test environment 缺少 route/router injection，导致 `route.params` 崩溃；已由 `ba830da` 修复。
- Element Plus `el-table` `DefaultRow` 与 `ModelProfile` handler 参数冲突，导致 production `vue-tsc` 失败；已由 `0a4462a` 修复。

## 当前 E-4 任务

进入 **2.2-E-4 Acceptance**：

1. 核对 E-2 Runtime / Evaluation Profile Resolution、cross-dimension Real Provider、CRUD / Organization scope / Audit / Trace evidence。
2. 核对 E-3 Frontend targeted Vitest 与 production build 的本轮实际 evidence。
3. 保持 Backend / Frontend / Browser Gate 独立，不用某一 Gate 替代另一 Gate。
4. Acceptance 文档不得使用未重新执行的旧结果冒充当前 evidence。
5. E-4 完成后再决定 Phase 2.2 是否关闭。

## 开发纪律

- 未实际执行的测试不得记录为 Passed。
- Baseline 只用于 regression comparison，不得通过修改 baseline 或降低阈值掩盖质量回归。
- 线上 Runtime 数据源继续使用数据库；JSON/JSONL 只用于版本化 evaluation dataset / result / baseline。
- 新业务代码不得新增具体模型名称硬编码；UI 测试中的模型字符串仅作为 fixture contract。
- 新增数据库表或字段必须先有 Migration。
- Secret 不进入数据库明文、CLI、报告或 Git。
- Phase 2.3 的完整 Provider Governance（路由/Fallback/成本/用量治理）仍保持产品路线候选，不因 2.2-E 提前实施。
- PowerShell `<PROFILE_UUID>` 占位符误用已记录在 `docs/04-errors/2026-08-22-phase-2-2-e-governed-evaluation-placeholder-command.md`；后续优先使用自动化 smoke script。
