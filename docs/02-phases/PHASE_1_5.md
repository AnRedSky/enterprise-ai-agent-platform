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

第一轮明确不强绑定 Temporal、MQ/Worker、复杂 DAG 调度、Multi-Agent orchestration、Saga、完整 Trigger 系统或可视化 Workflow Designer。

## 3. 任务拆解与历史内容归并

| ID | 内容 | 状态 | 历史内容归并 |
|---|---|---|---|
| 1.5-A | Workflow Definition Contract | 已完成 | Definition、Version、Lifecycle、RBAC/API contract |
| 1.5-B | Workflow Version / Publish Governance / Tenant Contract | 已完成 | Tenant FK、JWT tenant claim、Published Version、不可变版本、publish governance |
| 1.5-C | Workflow Execution State Machine | 已完成 | execution/node state、持久化、transition contract |
| 1.5-D | Workflow Runtime Integration | 已完成 | published version execution、input/agent/output node、owner/admin、tenant scope、runtime failure convergence |
| 1.5-E | Governance / Audit / Trace | 已完成 | workflow audit、workflow trace、owner/admin/tenant 查询隔离、migration 0017 |
| 1.5-F | Retry / Timeout / Idempotency / Concurrency / Deadline / Failure Recovery | 已完成 | Execution create/run UI、tenant scope、Trace read、Cancel、Retry lineage、Audit/Trace governance |
| 1.5-G | Circuit Breaker Real API | 已完成 | persistence、CLOSED/OPEN/HALF_OPEN、policy drift、fast-fail、probe quota、Retry/Deadline boundary、Real API |

## 4. 1.5-D Runtime Integration 历史实现

最小 Workflow Definition 支持 `input`、`agent`、`output` 串行节点；agent node 必须引用已发布 Agent，非 admin 用户只能执行自己拥有的 Agent。Execution 生命周期为 `pending → running → completed/failed/cancelled`，Node 生命周期为 `pending → running → completed/failed`。节点异常必须收敛到 Execution `failed` 并记录 error code/message。

`POST /api/v1/workflows/executions/{execution_id}/run` 要求 tenant scope、owner/admin RBAC、pending execution、创建时锁定的 Published Workflow Version。

## 5. 1.5-E Governance / Audit / Trace 历史实现

Workflow Execution 生命周期写入 `audit_logs`：created、run、completed、failed、cancelled；Workflow Trace 记录 execution/node state changes。新增 `workflow_trace_events` 和 migration `0017_workflow_governance_audit_trace`。Audit 使用独立 `workflow_execution_id`，不污染既有 Agent Runtime `execution_id` 语义。

Trace API：`GET /api/v1/runtime/executions/{execution_id}/trace`。Audit 查询支持 `workflow_id` / `workflow_execution_id`。owner 只能访问自身 Workflow，admin 只能跨 owner 但不能跨 tenant。

历史实现还记录了两次测试夹具整改：Governance Trace 引入 `created_by` 后补齐 fixture；随后继续补齐 `tenant_id / workflow_id / workflow_version_id / created_by / id`，生产代码不增加测试夹具降级逻辑。

## 6. 1.5-F Runtime Reliability / Frontend 历史实现

### F-01 Execution UI

Workflow Governance 管理端增加 JSON Input、Create Execution、Run Execution、Execution ID 回填、Node 状态刷新，并强制后端根据 `published_version_id` 选择已发布版本。

### F-02 Tenant Scope

Workflow tenant → Workflow Execution tenant → Workflow Runtime → Agent owner tenant 四层 scope 保持一致；即使 admin 也不能通过 Workflow Runtime 跨 tenant 解析 Agent。

### F-03 Trace

Execution Timeline 与 Workflow Trace 并行加载；Trace 读取继续复用既有 RBAC 和 Trace 数据模型，不创建第二套观察模型。

### F-04 Execution Governance

`pending/running` 支持 Cancel；`failed` 支持 Retry；Retry 创建新 Execution 并通过 `retry_of_execution_id` 保留血缘；Cancel/Retry 继续写入 Audit/Trace；tenant/RBAC 边界保持不变。

## 7. 1.5-G Circuit Breaker

状态机：

```text
CLOSED → OPEN → HALF_OPEN → CLOSED
             ↖      ↓
               OPEN
```

状态按 `tenant_id + circuit_key` 隔离并持久化 policy；Policy drift 返回 `409`。OPEN 必须在业务边界 Fast-Fail，错误码 `CIRCUIT_OPEN`，不得重复调用 Provider、错误进入 Node Retry 或错误消耗 Retry Budget。HALF_OPEN probe 受 `half_open_max_calls` 限制。

历史实现包含 `WorkflowCircuitState`、migration `0020_workflow_circuit_breaker`、`CircuitBreakerService`、数据库行锁、transient failure 分类以及 Retry/Runtime 异常边界修复。migration `0021_workflow_circuit_policy` 后 policy 持久化与 drift governance 完整闭环。

## 8. 验收门禁

- Backend pytest
- Alembic upgrade head
- API Scenario / Real API
- RBAC / Tenant isolation
- Frontend API Types / Vitest / build
- 前后端联调
- Backend / Frontend / Browser Gate 按当前治理规则独立执行

## 9. 迁移来源

本 Phase 内容逐份核对并归并自：

- `13-phase-1.5-workflow-governance-plan.md`
- `14-phase-1.5-g-circuit-breaker.md`
- `phase-1.5-d-workflow-runtime-integration.md`
- `phase-1.5-e-governance-audit-trace.md`
- `phase-1.5-f-vue-workflow-governance.md`
- `phase-1-5-f/001-workflow-execution-ui.md`
- `phase-1-5-f/002-workflow-runtime-tenant-scope.md`
- `phase-1-5-f/003-workflow-runtime-observability.md`
- `phase-1-5-f/004-workflow-execution-governance-controls.md`

A/B/C 以及最终 G 验收状态也与原 `PHASE_1_5` 基线和 Acceptance 记录核对。实际结果进入 `03-acceptance/PHASE_1_5_ACCEPTANCE.md`。

## 10. 当前状态

**Phase 1.5-A / B / C / D / E / F / G 均已完成，Phase 1.5 正式关闭。**