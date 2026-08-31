# Phase 2.10-II — Enterprise Operations Console / Operator Governance

## 1. 目标

在 Phase 2.10-I 完成 Runtime Notification、Metrics、SLO、Audit 与统一 Runtime Acceptance 后，继续推进 LT-03 Enterprise Operations Console，将现有 Runtime、Workflow、Agent、Trigger 与 Audit 能力收敛为可治理的企业运维工作台。

本阶段不重新实现已经稳定的 Runtime Notification、Metrics、Telemetry、Provider 或 Workflow 状态机，而是围绕现有 Backend Contract 建立统一的运维操作边界、诊断关联和高风险操作保护。

## 2. 当前状态

**开发中。II-01 Backend Operator Action Governance 已完成本地反馈验证；II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；II-03 Worker / Scheduler Diagnostics Backend 与 Frontend 第一切片已实现；II-04 Audit / Trace Correlation Backend 第一切片已实现，进入本地验证。**

Phase 2.10-I 已根据本地实际 Real Gate 反馈完成 Runtime Notification Lifecycle 收口。II-01 已通过本地 Alembic、Unit/API Contract、Real PostgreSQL Acceptance 与完整 Backend Regression。II-02 已通过开发者本地反馈的 Global Runtime Operations Unit / Real Gate 与完整 Backend Regression。

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
- Backend / Frontend Gate 均禁止自动启动或停止服务，测试数据自动生成和清理。

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
7. Agent correlation 只复用 `WorkflowVersion.definition.agent_id`，不新增第二套 Agent 关联事实。
8. Frontend 只消费 Backend Contract，不在页面复制状态聚合、tenant scope 或生命周期规则。

### 4.3 当前验证状态

II-02 Backend 已由开发者本地反馈确认通过；Frontend targeted Unit / Build、完整 Frontend Regression、Browser E2E 仍需按范围执行后再完成 Acceptance 收口。

## 5. 第三切片：II-03 Worker / Scheduler Diagnostics

### 5.1 Backend 第一切片

已实现 `RuntimeDiagnosticsService`，只读复用现有 `WorkflowFrontier` 与 `WorkflowTrigger` Durable Facts：

- Worker Frontier 状态、running / pending / completed / failed 统计；
- Worker lease active / expired / no-expiry 统计；
- Durable worker owner claim 聚合；
- 最近 Worker Frontier error 事实；
- Scheduler enabled / disabled scheduled trigger 统计；
- Scheduler pending Frontier backlog；
- scheduled trigger 配置摘要；
- Worker / Scheduler 当前没有 durable heartbeat 时统一返回 `unknown + NO_DURABLE_HEARTBEAT_FACT`；
- `/api/v1/runtime/diagnostics/worker` 与 `/api/v1/runtime/diagnostics/scheduler` 只读 API Contract；
- 所有租户范围均来自认证 Claims，不接受客户端 `tenant_id`；
- 不新增 Worker / Scheduler 生命周期状态机，不修改任何 Durable Fact。

### 5.2 测试与 Gate

- `tests/unit/test_runtime_diagnostics.py` 覆盖窗口边界、Worker liveness、lease / owner 聚合及 Scheduler posture；
- `tests/api_contract/test_runtime_diagnostics_contract.py` 覆盖只读路由 Contract；
- `scripts/test/phase-2.10/08_runtime_diagnostics_unit_gate.ps1` 提供独立 Unit / Contract Gate；
- Gate 禁止自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；
- 真实 PostgreSQL / API Acceptance 必须由后续本地服务已运行条件下执行，测试身份与业务数据由 fixture 自动创建和清理。

### 5.3 当前验证状态

**代码已提交，尚未宣称 Acceptance Passed。** 必须先执行本地 Unit Gate，再补充 tenant boundary 的 Real PostgreSQL / HTTP Acceptance；随后才能进入 II-03 Frontend Diagnostics 与完整联调。

## 6. 第四切片：II-04 Audit / Trace Correlation

### 6.1 Backend 第一切片

新增 `RuntimeAuditTraceCorrelationService`，只读复用现有 Workflow Execution、Workflow Trace、AuditLog 与 Operator Action 幂等事实，不新增第二套审计或 Trace 存储。

提供四条 tenant-scoped 深链：

- `GET /api/v1/runtime/correlations/executions/{execution_id}`：Execution → Trace / Audit / Operator Action；
- `GET /api/v1/runtime/correlations/traces/{trace_id}`：Trace → Execution / Audit / Operator Action；
- `GET /api/v1/runtime/correlations/audits/{audit_id}`：Audit → Execution / Trace / Operator Action；
- `GET /api/v1/runtime/correlations/operator-actions/{operator_action_id}`：Operator Action → Execution / Audit / Trace。

关联边界：

1. Tenant scope 只来自认证 Claims，客户端不能传入 `tenant_id`。
2. Execution、Trace、Audit 与 Operator Action 均只读查询，不修改任何 Durable Fact。
3. Operator Action 直接复用 `OperatorActionIdempotency`，通过 `resource_id` / `result_resource_id` 与 Workflow Execution 关联。
4. Audit 继续复用现有 `AuditLog.workflow_execution_id`；Trace 继续复用现有 `WorkflowTraceEvent.execution_id` / `trace_id`。
5. Trace / Audit 集合使用 `created_at + id` 稳定排序，并分别提供独立分页参数，避免深链页面出现不稳定分页。
6. 跨租户资源统一表现为不存在，阻止通过深链探测其他租户事实。

### 6.2 测试与 Gate

- `tests/unit/test_runtime_audit_trace_correlation.py` 覆盖分页边界、正向关联和反向深链；
- `tests/api_contract/test_runtime_audit_trace_correlation_contract.py` 覆盖四条 GET-only Contract；
- `tests/api_real/test_runtime_audit_trace_correlation_acceptance.py` 覆盖 Execution / Trace / Audit / Operator Action 的 tenant isolation 与双向关联；
- `scripts/test/phase-2.10/10_audit_trace_correlation_unit_gate.ps1`；
- `scripts/test/phase-2.10/11_audit_trace_correlation_real_gate.ps1`；
- 两个 Gate 均禁止自动启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；Acceptance 数据自动生成和清理。

### 6.3 当前验证状态

**Backend 第一切片代码已形成，尚未宣称本地 Gate / Acceptance Passed。** 开发者本地执行必须依次完成 Unit / Contract、Real PostgreSQL Acceptance 与 Backend Regression；通过后再进入 II-04 Frontend Correlation UI 与 Browser E2E。

## 7. 后续切片

### II-05 Controlled Batch Operations

- 批量 Retry / Cancel / Replay 等高风险操作；
- 权限、确认、幂等、部分失败结果和审计；
- 禁止前端复制批量业务规则。

## 8. 完成判定

每个切片必须同时满足：

- Backend Contract、Service、Repository / Durable Facts 边界完成；
- tenant boundary 有 unit + Real API 覆盖；
- 高风险操作具备权限/状态校验与审计事实；
- Frontend 使用 Backend Contract，不复制业务规则；
- Frontend Vitest 与 Build 通过；
- Backend Regression 与 Real API Gate 通过；
- 范围需要时执行 Browser E2E；
- 测试 Gate 不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，测试数据自动生成和清理。

## 9. 开发顺序

```text
Operator Action Contract
        ↓
Global Runtime Operations Contract
        ↓
Worker / Scheduler Diagnostics Contract
        ↓
Audit / Trace Correlation Contract
        ↓
Backend Domain / API Contract
        ↓
Unit + Integration + Real API
        ↓
Frontend API Types
        ↓
Operations UI / Diagnostics UI / Correlation UI
        ↓
Frontend Regression / Build
        ↓
Backend Regression / Real API
        ↓
Browser E2E
        ↓
Phase Acceptance
```
