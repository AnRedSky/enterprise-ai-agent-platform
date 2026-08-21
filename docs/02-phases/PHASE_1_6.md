# Phase 1.6 — Workflow Production Hardening / Trigger Contract

## 1. 阶段目标

建立 Workflow 从内部 Execution API 向稳定业务入口演进所需的 Trigger Contract，同时保持 FastAPI + PostgreSQL 单体边界，不提前引入 MQ、Worker、Cron 或具体分布式 Workflow Engine。

```text
Published Workflow
 ↓
Trigger Contract
 ↓
Tenant / RBAC / Lifecycle validation
 ↓
Idempotency / Concurrency governance
 ↓
Workflow Execution
 ↓
Audit / Trace
 ↓
Frontend Workflow Governance UI
 ↓
Browser E2E
```

## 2. 范围

- Trigger domain contract
- Manual/API Trigger 与 Execution API 边界
- Trigger identity / tenant scope
- enabled / disabled lifecycle
- Published Workflow Version binding
- request validation
- idempotency
- audit / trace
- failure code boundary
- Backend Contract / Migration / pytest / Real API
- Frontend API Types / Vitest / Workflow Governance UI
- 独立 Browser / Frontend-Backend E2E

不实现 MQ、Worker、Cron Scheduler、Event Bus、分布式任务队列、Temporal/Airflow、高级 DAG、Saga、复杂 Policy DSL 或拖拽编辑器。

## 3. 任务拆解与历史内容归并

| ID | 内容 | 状态 | 迁移来源 |
|---|---|---|---|
| 1.6-A | Trigger Contract / Backend | 已完成并关闭 | `15-phase-1.6-workflow-production-hardening-plan.md` |
| 1.6-B | Frontend Contract / Workflow Governance UI | 已完成并关闭 | `15-phase-1.6-workflow-production-hardening-plan.md`、`16-phase-1.6-b-frontend-workflow-governance-ui-contract.md` |
| 1.6-C | Frontend / Backend Integration & Browser E2E | 已完成并关闭 | `17-phase-1.6-c-frontend-backend-e2e-contract.md` |
| 1.6-D | 独立历史文档 | **未发现对应独立 Phase 1.6-D 文档** | 仅现有 Phase/Acceptance 对 Phase 1.6 做 A-C 归并；不凭空补造 D 内容 |

## 4. Trigger Contract

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

第一轮 `trigger_type=manual`，`status=enabled|disabled`。Tenant / Workflow / creator 由认证上下文和 Service 确定，客户端不得提交 Tenant。

Trigger 只能作用于当前 Tenant 可访问 Workflow，只能调用 Published Workflow，并复用 Execution State Machine、Idempotency、Concurrency、Reliability、Audit / Trace。

## 5. Frontend Contract / UI

`frontend/src/api/workflows.ts` 提供 Trigger TypeScript contract、list/create/update/delete/invoke API；invoke 支持 `Idempotency-Key`。UI `/workflows/triggers` 支持 Workflow 选择、Trigger inventory、创建、Enable/Disable、删除、Config JSON、Invoke Input、Invoke 和最近一次 Execution 摘要。

UI 不实现 Tenant、Published Version、Retry、Circuit Breaker 等后端治理规则，也不直接调用 Execution Runtime。

## 6. Browser E2E Contract

真实链路：

```text
Browser → Vue 3 UI → Frontend API client → FastAPI HTTP → Workflow Trigger → Workflow Execution → PostgreSQL
```

场景覆盖注册/登录、创建并发布 Workflow、进入 `/workflows/triggers`、创建 manual Trigger、Invoke、验证 completed Execution、Disable 后禁止 Invoke、Re-enable、Delete。

治理边界验证 Tenant 不由前端提交，UI 通过 Trigger API，不直接调用 Execution Runtime，Execution 结果来自真实 Backend response。

## 7. 历史实际发现与修复

Phase 1.6-C 记录了 Playwright project 未显式命名、真实 HTTP 状态码断言不一致、Element Plus Select 交互、Published Workflow locator strict mode、Delete confirmation 多按钮等实际测试实现问题，均通过测试实现修正。

最终 Browser Gate 历史结果：`1 passed (3.9s)`；同时历史记录保留 Backend Real API `14 passed`、Frontend Vitest `50 passed`、Frontend build PASS、Trigger Real HTTP PASS、Frontend UI PASS。上述为历史实际反馈，不代表本次文档迁移重新执行。

## 8. Gate

Backend：pytest → migration/head → Real API。

Frontend：Vitest → production build。

Browser：真实 Browser → Vue → Backend HTTP；不得复制 Backend / Frontend Gate。

## 9. 迁移来源

- `15-phase-1.6-workflow-production-hardening-plan.md`
- `16-phase-1.6-b-frontend-workflow-governance-ui-contract.md`
- `17-phase-1.6-c-frontend-backend-e2e-contract.md`
- `03-acceptance/PHASE_1_6_ACCEPTANCE.md`（历史状态核对）

## 10. 当前状态

**Phase 1.6 已关闭。** 当前 Phase 文档不补造未发现的 1.6-D 历史内容；如果后续发现遗漏源文档，应先补入迁移矩阵并核对内容后再更新本文件。