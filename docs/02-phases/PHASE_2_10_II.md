# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。II-01 Backend Operator Action Governance 已完成本地反馈验证；II-02 Backend Domain / API Contract 与 Frontend Operations 第一切片已实现，当前进入本地验证与联调。**

Phase 2.10-I 已根据本地实际 Real Gate 反馈完成 Runtime Notification Lifecycle 收口。II-01 已通过本地 Alembic、Unit/API Contract、Real PostgreSQL Acceptance 与完整 Backend Regression；当前推进 II-02。

## 3. 第一切片：Operator Action Governance

### 3.1 目标

为 Runtime / Workflow / Trigger 运维操作建立统一的操作治理 Contract，避免前端自行判断权限、状态或重复实现生命周期规则。

### 3.2 Backend / Acceptance 状态

- 新增 `OperatorActionGovernanceService`，统一维护 Workflow Execution / Trigger 操作定义；
- Workflow Execution 已接入 Run / Cancel / Retry / Resume 统一 Operator Action 入口；
- Trigger 已接入 Enable / Disable / Delete / Invoke 统一 Operator Action 入口；
- 高风险操作统一要求 `confirm=true`；
- Retry / Trigger Invoke 要求 `Idempotency-Key`；
- 新增 tenant-scoped Operator Action 幂等事实表与 Alembic migration；
- Operator Action 继续委托现有 `WorkflowExecutionService` / `WorkflowTriggerService`，不复制生命周期状态机；
- Operator Action 结果写入现有 `AuditLog`；
- 本地反馈已确认：Alembic head 为 `0049_operator_action_idempotency`、Unit/API Contract 16 passed、Real PostgreSQL Acceptance 2 passed、完整 Backend Regression `971 passed, 3 skipped, 68 deselected`。

## 4. 第二切片：II-02 Global Runtime Operations

### 4.1 Backend / Frontend 实现

新增 `GlobalRuntimeOperationsService`，只读聚合现有 Durable Workflow / Execution / Frontier / Trigger facts，不创建第二套生命周期状态机。

提供：

- tenant-scoped 全局 Execution 状态摘要：pending / running / completed / failed / cancelled；
- active / recovery 统计及最近 Execution 列表；
- Workflow 状态摘要；
- Trigger 状态及 enabled scheduled trigger 数量；
- Worker Frontier running / pending / lease / expired lease / active worker owner 统计；
- Scheduler durable backlog 与 enabled scheduled trigger 统计；
- `workflow_id` / `agent_id` / `trigger_id` / `execution_id` / `execution_status` 关联查询参数；
- Worker / Scheduler process liveness 明确返回 `unknown + NO_DURABLE_HEARTBEAT_FACT`，禁止从业务活动伪造进程健康状态；
- `/api/v1/runtime/global` read-only API Contract；
- Frontend `runtimeOperationsApi.global` 类型化接入；
- `/runtime/operations/global` 全局 Runtime Operations 只读页面；
- Unit / API Contract / PostgreSQL Real Acceptance 测试；
- Frontend Component Contract 测试与独立 Frontend Gate；
- Backend / Frontend Gate 均禁止自动启动或停止服务，测试数据自动创建和清理。

### 4.2 设计边界

```text
Authenticated Tenant Context
        ↓
Global Runtime Query Contract
        ↓
Workflow / Execution / Frontier / Trigger Durable Facts
        ↓
Execution / Workflow / Worker / Scheduler Posture
        ↓
Runtime Operations UI / Diagnostics
```

强制约束：

1. Tenant scope 只能来自认证身份上下文。
2. 查询只读，不修改 Workflow / Execution / Trigger / Frontier 状态。
3. Workflow Execution 生命周期继续由 `WorkflowExecutionService` 管理。
4. Trigger 生命周期继续由 `WorkflowTriggerService` 管理。
5. Worker posture 只读取 Durable Frontier claim facts。
6. 当前没有 scheduler/worker heartbeat durable contract 时，必须报告 `unknown`，不得把“有数据活动”解释为服务存活。
7. Agent correlation 只复用现有 `WorkflowVersion.definition.agent_id`，不新增第二套 Agent 关联事实。
8. Frontend 只消费 Backend Contract，不在页面复制状态聚合、tenant scope 或生命周期规则。

### 4.3 当前验证状态

代码、测试与 Frontend UI 已提交到 `main`，但本轮尚未在用户本地环境执行 II-02 Frontend / Backend Gate，因此 **暂不得标记 Acceptance Passed**。

## 5. 后续切片

### II-03 Worker / Scheduler Diagnostics

- Worker lease / claim / concurrency 状态；
- Scheduler loop / trigger / misfire 状态；
- 失败恢复与运行态诊断；
- 不暴露内部连接和 Secret。

### II-04 Audit / Trace Correlation

- Execution → Trace → Audit 双向关联；
- Operator Action → Audit → Execution 关联；
- 稳定分页、筛选和深链。

### II-05 Controlled Batch Operations

- 批量 Retry / Cancel / Replay 等高风险操作；
- 权限、确认、幂等、部分失败结果和审计；
- 禁止前端复制批量业务规则。

## 6. 完成判定

每个切片必须同时满足：

- Backend Contract、Service、Repository / Durable Facts 边界完成；
- tenant boundary 有 unit + Real API 覆盖；
- 高风险操作具备权限/状态校验与审计事实；
- Frontend 使用 Backend Contract，不复制业务规则；
- Frontend Vitest 与 Build 通过；
- Backend Regression 与 Real API Gate 通过；
- 范围需要时执行 Browser E2E；
- 测试 Gate 不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，测试数据自动生成和清理。

## 7. 开发顺序

```text
Operator Action Contract
        ↓
Global Runtime Operations Contract
        ↓
Backend Domain / API Contract
        ↓
Unit + Integration + Real API
        ↓
Frontend API Types
        ↓
Operations UI
        ↓
Frontend Regression / Build
        ↓
Backend Regression / Real API
        ↓
Browser E2E
        ↓
Phase Acceptance
```
