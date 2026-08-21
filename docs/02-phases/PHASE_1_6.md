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

不实现 MQ、Worker、Cron Scheduler、Event Bus、分布式任务队列、Temporal/Airflow、高级 DAG、Saga、复杂 Policy DSL 或拖拽编辑器。

## 3. Trigger Contract

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

第一轮 `trigger_type=manual`，`status=enabled|disabled`。Tenant / Workflow / creator 由认证上下文和 Service 确定。

Trigger 必须只能作用于当前 Tenant 可访问 Workflow，只能调用 Published Workflow，并复用 Execution State Machine、Idempotency、Concurrency、Reliability、Audit / Trace。

## 4. Frontend

新增 Trigger API Types 与 Workflow Governance UI，支持 Workflow 选择、Trigger inventory、创建、Enable/Disable、删除、Config JSON、Invoke Input、Execution 摘要。Frontend 不提交 Tenant，也不实现业务幂等和 Authentication。

## 5. Gate

Backend：pytest → migration/head → Real API。

Frontend：Vitest → production build。

Browser：真实 Browser → Vue → Backend HTTP；不得复制 Backend / Frontend Gate。

## 6. 完成记录

Phase 1.6 已关闭。历史 1.6-A/B/C/D 任务文档统一并入本 Phase；实际验收结果归 `03-acceptance/PHASE_1_6_ACCEPTANCE.md`。