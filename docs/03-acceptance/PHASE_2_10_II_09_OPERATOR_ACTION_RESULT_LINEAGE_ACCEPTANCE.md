# Phase 2.10-II / II-09 Acceptance — Operator Action Result Lineage

## 验收对象

验证 Retry Operator Action 在真实 PostgreSQL 中形成以下不可断裂的持久化链：

`OperatorActionIdempotency -> AuditLog -> WorkflowExecution -> WorkflowTraceEvent`。

## 自动化测试

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

## Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
```

Gate 不自动启动任何受保护服务；PostgreSQL 仅执行 readiness 检查。

## 测试事实

测试自动创建 Tenant、User、published Workflow / WorkflowVersion、failed WorkflowExecution 和随机 Idempotency-Key，然后通过正式 `OperatorActionGovernanceService` 执行 Retry，并通过正式 `RuntimeAuditTraceCorrelationService` 回读关联事实。

## 验收断言

1. Retry Result Execution 状态为 `pending`，且 `retry_of_execution_id` 指向原始 failed Execution；
2. Operator Action 状态为 `succeeded`；
3. `result_resource_type=workflow_execution` 且 `result_resource_id` 指向 Retry Execution；
4. Operator Audit 的目标资源仍指向原始 Execution，同时 `workflow_execution_id` 指向结果 Execution；
5. Audit 的 Trace 标识与结果 Execution 的 Trace 事实可以关联；
6. `by_operator_action()` 能返回结果 Execution、Operator Audit 与 Trace 集合，并保留 `focus_operator_action_id`；
7. 测试自动清理全部数据。

## 当前状态

实现已提交，等待开发者在本地 PostgreSQL 环境执行上述 Acceptance 与 Gate；未在仓库端虚构本地通过结果。
