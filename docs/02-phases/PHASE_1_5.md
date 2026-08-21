# Phase 1.5 — Workflow / Governance

## 1. 阶段目标

建立与 Agent Runtime、RBAC、Tool Runtime、Observability 解耦的 Workflow / Governance 领域边界，形成可逐项验收的执行闭环。

```text
Workflow Definition
 ↓
Workflow Version
 ↓
Lifecycle / Publish Governance
 ↓
Tenant Contract
 ↓
Workflow Execution State Machine
 ↓
Runtime Integration
 ↓
Governance / Audit / Trace
 ↓
Circuit Breaker Governance
```

## 2. 领域边界

Workflow 负责定义、版本、节点/边、生命周期、发布版本、Execution State、Runtime 入口、Tenant scope 和 Retry / Timeout / Circuit Breaker Contract。

Governance 负责发布状态、Version / Publish 记录、RBAC / Tenant isolation、Audit、Runtime 可追溯和 Circuit Breaker policy persistence / drift governance。

## 3. 任务拆解

| ID | 内容 | 状态 |
|---|---|---|
| 1.5-A | Workflow Definition Contract | 已完成 |
| 1.5-B | Workflow Version / Publish Governance / Tenant Contract | 已完成 |
| 1.5-C | Workflow Execution State Machine | 已完成 |
| 1.5-D | Workflow Runtime Integration | 已完成 |
| 1.5-E | Governance / Audit / Trace | 已完成 |
| 1.5-F | Retry / Timeout / Idempotency / Concurrency / Deadline / Failure Recovery | 已完成 |
| 1.5-G | Circuit Breaker Real API | 已完成 |

## 4. Circuit Breaker

状态机：

```text
CLOSED → OPEN → HALF_OPEN → CLOSED
             ↖      ↓
               OPEN
```

状态按 `tenant_id + circuit_key` 隔离并持久化 policy；Policy drift 返回 `409`。OPEN 必须在业务边界 Fast-Fail，错误码 `CIRCUIT_OPEN`，不得重复调用 Provider、错误进入 Node Retry 或错误消耗 Retry Budget。HALF_OPEN probe 受 `half_open_max_calls` 限制。

## 5. API / Runtime

Workflow Registry / Version API 和 Execution State Machine 统一以 Tenant scope、Published Version、Idempotency、Concurrency、Reliability Governance 为边界。Execution 必须关联具体 Workflow Version。

## 6. 验收门禁

- Backend pytest
- Alembic upgrade head
- API Scenario / Real API
- RBAC / Tenant isolation
- Frontend API Types / Vitest / build
- 前后端联调
- Backend / Frontend / Browser Gate 按当前治理规则独立执行

实际 Phase 1.5-G 验收事实进入 `03-acceptance/PHASE_1_5_ACCEPTANCE.md`。