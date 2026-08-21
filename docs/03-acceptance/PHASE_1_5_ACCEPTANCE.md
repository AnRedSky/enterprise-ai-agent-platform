# Phase 1.5 — Acceptance

## 1. 范围

Workflow Definition / Version / Publish、Tenant Governance、Execution State Machine、Runtime Integration、Governance / Audit / Trace、Retry / Timeout / Idempotency / Concurrency / Deadline、Circuit Breaker。

## 2. Final Acceptance — 1.5-G

开发者实际结果（原阶段记录）：

```text
uv run alembic upgrade head
→ 0020_workflow_circuit_breaker -> 0021_workflow_circuit_policy 成功

uv run pytest -q
→ 209 passed, 11 deselected in 3.44s

backend/scripts/test/api-real/01_run_real_api_tests.ps1
→ 11 passed in 17.62s
→ [PASS] Real API gate completed. Frontend/backend integration may proceed.
```

上述结果作为历史真实反馈保留，不因本次文档迁移重新执行而改变。

## 3. 1.5-A/B/C/D/E/F 历史验收事实

- A：Workflow Definition、Version、Lifecycle、RBAC/API contract 已建立。
- B：Tenant contract 已建立；Workflow/User Tenant FK、JWT tenant claim、Published Version 和 publish governance 已形成。
- C：Execution / Node State Machine 已持久化。
- D：已发布 Workflow Version → Runtime 的最小执行闭环已形成；支持 input/agent/output 串行节点和失败收敛。
- E：Workflow Audit / Trace 已形成独立治理闭环，migration `0017_workflow_governance_audit_trace`。
- F：Execution create/run 管理端、tenant scope、Trace 读取、Cancel、Retry lineage 和 Audit/Trace governance 已形成；测试夹具问题已按真实 Domain Contract 修复。

## 4. 1.5-G Circuit Breaker Contract

- CLOSED → OPEN → HALF_OPEN → CLOSED
- policy 按 `tenant_id + circuit_key` 隔离
- policy drift `409`
- OPEN `CIRCUIT_OPEN` fast-fail
- HALF_OPEN probe quota
- transient failure 才计入阈值
- OPEN 不错误消耗 Retry budget
- probe success → CLOSED
- probe failure → OPEN
- Retry / Workflow Deadline 边界保持独立

## 5. 历史失败与修复证据

原 1.5-G 记录过以下实际失败：

```text
uv run pytest -q
204 passed, 1 failed, 10 deselected

Real API Gate
8 passed, 2 failed
```

失败涉及 Retry budget 原始异常保持、`workflow.node.retry` Audit action、独立 Execution 首次 `CIRCUIT_OPEN` Node attempt 应为 1。随后提交 `e0fff63ca6fdd56cb40bd7bb03f28b779b34d7a3` 修复：新 Node Execution 显式 `attempt=1`、Retry 同时记录治理 action、terminal Execution 不再错误包装原始 Runtime 异常。最终上述 Final Acceptance Gate 已通过。

## 6. 验收结论

原 Phase 1.5 文档记录 1.5-A～G 全部完成，Phase 1.5 正式关闭。后续阶段状态以 `PROJECT_STATUS.md` 为准。

## 7. 迁移来源

- `13-phase-1.5-workflow-governance-plan.md`
- `14-phase-1.5-g-circuit-breaker.md`
- `phase-1.5-d-workflow-runtime-integration.md`
- `phase-1.5-e-governance-audit-trace.md`
- `phase-1.5-f-vue-workflow-governance.md`
- `phase-1-5-f/001-workflow-execution-ui.md`
- `phase-1-5-f/002-workflow-runtime-tenant-scope.md`
- `phase-1-5-f/003-workflow-runtime-observability.md`
- `phase-1-5-f/004-workflow-execution-governance-controls.md`
