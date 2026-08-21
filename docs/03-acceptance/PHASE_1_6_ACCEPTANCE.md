# Phase 1.6 — Acceptance

## 1. 范围

Trigger Contract、Manual/API Trigger、Tenant/RBAC/Lifecycle、Published Workflow binding、Idempotency/Concurrency、Audit/Trace、Frontend Workflow Governance UI 与真实浏览器联调。

## 2. 历史实际验收事实

### 1.6-A Backend

历史基线记录 Phase 1.6-A Backend Contract 已由开发者本地两道 Backend Gate 验收通过并关闭。Trigger API 包含 list/create/get/update/delete/invoke；Tenant 来自认证上下文；Trigger 只能调用 Published Workflow；invoke 复用 Execution State Machine、Idempotency/Concurrency/Reliability、Audit/Trace。

### 1.6-B Frontend

历史 B 文档记录 Workflow Trigger Governance UI 已实现：Workflow 选择、Trigger CRUD、enabled/disabled、Config JSON、Invoke Input、Execution 摘要，以及 `Idempotency-Key`。Frontend 不提交 tenant_id，也不绕过 Trigger API 调用 Runtime。

原 B 文档在实现阶段明确写过 Frontend Gate 待本地执行；后续 C 文档提供了最终独立 Gate 的实际通过结果，因此本 Acceptance 以最终实际结果为准，不把中间 pending 当作最终失败。

### 1.6-C Browser E2E

真实链路：

```text
Browser → Vue 3 UI → Frontend API client → FastAPI HTTP → Workflow Trigger → Workflow Execution → PostgreSQL
```

最终 Browser Gate 实际结果：

```text
✓ 1 [Desktop Chrome] … Workflow Trigger Governance completes the real browser contract
1 passed (3.9s)
[PASS] Phase 1.6-C browser E2E gate completed.
```

历史同时记录：

```text
Backend Real API       PASS — 14 passed
Frontend Vitest        PASS — 50 passed
Frontend build         PASS
Trigger Real HTTP      PASS
Frontend UI            PASS
Browser E2E             PASS — 1 passed
```

这些数字与状态是历史证据，本次 Docs Refactor 不重新执行。

## 3. E2E 中实际发现并修复的问题

- Playwright project 未显式命名。
- E2E 注册状态码断言与真实 Backend HTTP Contract 不一致。
- Element Plus Workflow Select 内部 input 被 selected item 拦截。
- Published Workflow 文本同时出现在页面和 dropdown，导致 locator strict mode violation。
- Delete confirmation 存在多个“确定”按钮，locator 未限定到可见 MessageBox。

这些属于 E2E 测试实现问题，已通过测试代码修复；其中 Playwright project 缺失另有历史 error-tracking 记录。

## 4. 验收门禁结构

Backend：pytest → migration/head → Real API。

Frontend：Vitest → production build。

Browser：真实 Browser → Vue → Backend HTTP，独立于前两层。

E2E 不复制 Backend regression、Migration、Backend Real API 或 Frontend regression。

## 5. 1.6-D 记录状态

本次从最新 `main` 的完整 Git tree 和相关 Phase 文档逐项核对，未发现独立的 `Phase 1.6-D` 文档或可对应的独立 D 任务记录。因此不新增虚构内容。当前 Phase 1.6 的历史闭环证据实际覆盖 A/B/C。

## 6. 结论

当前 `PROJECT_STATUS.md` 记录 Phase 1.6 已正式关闭。迁移时不根据旧计划重新声称测试通过；只保留已经存在的实际验收事实。

## 7. 迁移来源

- `15-phase-1.6-workflow-production-hardening-plan.md`
- `16-phase-1.6-b-frontend-workflow-governance-ui-contract.md`
- `17-phase-1.6-c-frontend-backend-e2e-contract.md`
