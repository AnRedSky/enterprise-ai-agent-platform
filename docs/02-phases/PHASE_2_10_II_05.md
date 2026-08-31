# Phase 2.10-II / II-05 — Controlled Batch Operations Backend

## 1. 目标

在既有 Operator Action Governance 基础上提供受控批量运维能力，使运维调用可以一次提交多个同类型资源，同时保持既有 Workflow Execution / Trigger 生命周期、权限、tenant boundary、确认和幂等规则不变。

## 2. 架构原则

```text
Batch Operator Action API
        ↓
BatchOperatorActionService
        ↓
OperatorActionGovernanceService
        ↓
┌───────────────────────────┐
│ WorkflowExecutionService  │
│ WorkflowTriggerService    │
└───────────────────────────┘
        ↓
Existing Durable Facts
```

批量层只负责编排，不实现第二套状态机。

## 3. Backend 第一切片

### 3.1 请求边界

- `resource_type` 仅允许 `workflow_execution` / `workflow_trigger`；
- `action` 必须来自既有 Operator Action Registry；
- 单批最多 100 个资源；
- `resource_ids` 不允许重复；
- 请求体不接受 `tenant_id`，租户始终来自认证上下文；
- 高风险操作继续由 `OperatorActionGovernanceService` 强制 `confirm=true`；
- Retry / Trigger Invoke 继续要求 `Idempotency-Key`。

### 3.2 执行语义

- 每个资源独立执行；
- 一个资源失败或因 tenant / state / permission 被拒绝，不阻止后续合法资源；
- 返回 `succeeded_count`、`rejected_count`、`failed_count` 与逐项结果；
- 批量 Retry / Invoke 从批次幂等键稳定派生单项幂等键；
- 实际状态变更继续调用现有 Workflow / Trigger Domain Service；
- 不新增数据库 Durable Fact，因此本切片无需新增 Alembic migration。

## 4. HTTP Contract

```text
POST /api/v1/runtime/operator-actions/batch
```

请求字段：

```json
{
  "resource_type": "workflow_execution",
  "action": "cancel",
  "resource_ids": ["<uuid>", "<uuid>"],
  "confirm": true,
  "reason": "operator reason",
  "input_data": {}
}
```

响应包含：

```text
resource_type
action
total
succeeded_count
rejected_count
failed_count
items[]
```

## 5. 测试

### Unit

```powershell
cd backend
uv run pytest -q tests/unit/test_batch_operator_actions.py
```

### API Contract

```powershell
cd backend
uv run pytest -q tests/api_contract/test_batch_operator_actions_contract.py
```

### Real PostgreSQL

```powershell
cd backend
uv run pytest -q -m real_api tests/api_real/test_batch_operator_actions_acceptance.py --tb=short
```

### Unit Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\test\\phase-2.10\\12_controlled_batch_operations_unit_gate.ps1
```

### Real Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\\scripts\\test\\phase-2.10\\13_controlled_batch_operations_real_gate.ps1
```

## 6. 服务边界

Gate 只探测本地前置条件，不创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。Acceptance 测试自动创建并清理测试身份和业务事实，不要求手工填写 ID。

## 7. 当前验收状态

Unit Gate 已由开发者本地反馈确认通过：Unit/API Contract 9 passed，Backend targeted regression 38 passed。

Real Gate 已执行并确认业务断言进入验收流程，但测试在 `finally` 清理阶段因 `integration_events_tenant_id_fkey` 外键约束失败而未通过。根因是 `workflow_execution.cancel` 会产生 Durable Integration Event，而 Acceptance fixture 原清理顺序遗漏了 `IntegrationEventRecord`。

已修复 Acceptance fixture：删除测试租户前先删除其 `IntegrationEventRecord`；Webhook Delivery 对 Integration Event 使用 `ON DELETE CASCADE`，不新增第二套清理逻辑。

**当前状态：修复已提交，等待开发者本地重新执行 Real Acceptance / Real Gate 与 Backend Regression；尚未宣称 II-05 Acceptance Passed。**
