# Phase 1.6 — Acceptance

## 1. 范围

Trigger Contract、Manual/API Trigger、Tenant/RBAC/Lifecycle、Published Workflow binding、Idempotency/Concurrency、Audit/Trace、Frontend Workflow Governance UI 与真实联调。

## 2. 验收门禁

Backend：pytest → migration/head → Real API。

Frontend：Vitest → production build。

Browser：真实 Browser → Vue → Backend HTTP，独立于前两层。

## 3. 历史任务

1.6-A Trigger Contract、1.6-B Frontend Contract/UI、1.6-C Frontend/Backend E2E Contract 等旧根级文档统一并入本 Acceptance。

## 4. 结论

当前 `PROJECT_STATUS.md` 记录 Phase 1.6 已正式关闭。迁移时不根据旧计划重新声称测试通过；只保留已经存在的实际验收事实。