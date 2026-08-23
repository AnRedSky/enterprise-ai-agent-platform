# Phase 2.2 Acceptance — Retrieval Production Quality

> 状态：**E-4 Acceptance Passed / Phase 2.2 关闭**。
> 本结论仅基于开发者在当前 `main` 修复集上实际执行并反馈的 Backend Real API、Frontend Regression 与 Model Provider/Profile Browser E2E 三层 Gate；未执行的 Gate 不得标记 Passed。

## 1. E-2 Acceptance Evidence

开发者此前本地实际反馈：

```text
13 targeted tests passed
Migration head: 0027_retrieval_evaluation_vector_space
Backend regression: 323 passed, 31 deselected
Real HTTP API: 31 passed
Standalone Real API Gate: 31 passed
Governed smoke: status=passed
Profile A: nomic-embed-text:latest / 768
Profile B: qwen3-embedding:0.6b / 1024
retrieval_mode=real-provider-pgvector
retrieval_execution_path=runtime-service
fallback_count=0 / fallback_used=false
Profile B quality_gate=failed because model/dimension/model_profile_id identity changed; this is expected regression evidence
```

`Profile B quality_gate=failed` 不能单独解释为测试失败：Smoke 顶层 `status=passed`，其目的就是验证 governed identity 改变时不能复用 Profile A baseline。

### E-2 结论

- [x] Cross-dimension Evaluation Vector Space 可实际使用 768 / 1024 Profile。
- [x] Production `knowledge_chunks` 未被 evaluation dimension 改写。
- [x] Profile / Provider / model / dimension identity 进入 evaluation report / baseline regression。
- [x] Backend regression / migration / Real API Gate 均有本地实际证据。
- [x] Governed smoke 实际通过，且未下载模型。
- [x] fallback 未被用于伪造 vector quality success。
- [x] Secret 不进入 report / trace / audit / Git。

因此 **E-2 Passed**。

## 2. E-3 Frontend Acceptance

### 2.1 已提交实现

- [x] Frontend Model Provider/Profile API types/client。
- [x] Organization-scoped Provider/Profile 管理页。
- [x] Provider CRUD UI。
- [x] Profile CRUD UI。
- [x] Chat / Embedding dimension boundary。
- [x] Credential reference 仅显示引用，不回显 Secret。
- [x] Frontend API/UI Vitest。
- [x] vue-router test environment injection 修复。
- [x] Element Plus `DefaultRow` / `ModelProfile` production type boundary 修复。

### 2.2 开发者实际执行证据

```text
Frontend Regression Gate:
  18 test files passed
  75 tests passed
  vue-tsc -b passed
  Vite production build passed
```

此前 targeted Vitest：

```text
tests/api/modelProviders.test.ts + tests/views/ModelProviders.test.ts
2 test files passed
6 tests passed
```

因此 **E-3 Passed**。

## 3. E-4 三层 Gate 实际 Acceptance Evidence

开发者在当前修复后的 `main` 上实际反馈：

### 3.1 Backend Real API Gate

```text
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\01_run_real_api_tests.ps1

32 passed in 58.51s
[PASS] Real API gate completed.
```

该 Gate 覆盖 Provider/Profile CRUD、Organization scope、member authorization、AuditLog 等真实 HTTP/数据库链路。此前 member token fixture 边界问题已由 `448e2f8` 修复，并在本轮 32/32 通过中得到实际验证。

### 3.2 Frontend Regression Gate

```text
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_frontend_regression_gate.ps1

18 test files passed
75 tests passed
vue-tsc -b passed
Vite production build passed
[PASS] Frontend regression gate completed.
```

本轮同时清理了 `AuditLogPanel` error-path 测试的预期 `console.error` 噪声；测试现在显式断言 error-path 日志并在单测范围内隔离 console mock，不改变生产错误处理逻辑。

### 3.3 Model Provider/Profile Browser E2E

```text
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\02_run_model_provider_governance_e2e.ps1

Running 2 tests using 1 worker
2 passed (8.1s)
[PASS] Phase 2.2-E-4 Model Provider/Profile Browser contract completed.
```

覆盖：

- owner Provider/Profile CRUD。
- Organization-scoped real APIs。
- member 管理入口隐藏。
- Profile type selector 实际浏览器交互。

此前 selector pointer interception 问题已由 `be5b9ca` 修复，并在本轮 2/2 Browser E2E 通过中得到实际验证。

## 4. E-4 Acceptance Decision

E-4 所需证据全部满足：

- [x] E-2 Runtime / Evaluation Profile Resolution 与 cross-dimension Real Provider evidence。
- [x] Provider/Profile CRUD + Organization scope + Audit。
- [x] Frontend targeted Vitest。
- [x] Frontend Regression Gate。
- [x] Backend Real API Gate。
- [x] Model Provider/Profile 专项 Browser E2E。
- [x] member authorization boundary。
- [x] Profile selector 浏览器交互。
- [x] Secret non-disclosure boundary。

因此 **E-4 Passed，Phase 2.2 可正式关闭**。

## 5. 后续阶段边界

Phase 2.2 关闭后，项目可进入 Product Roadmap 定义的 **Phase 2.3 Model Provider Governance**，但必须先满足其进入条件：明确成本口径、路由策略与 Provider Contract。Phase 2.3 的 routing / fallback / model whitelist / cost / usage governance 不得从 2.2 实现中“顺便扩展”而绕过独立 Contract。

Phase 2.4 Durable Scheduler、Phase 2.5 Advanced Workflow Orchestration 等候选阶段继续保持未立项状态。
