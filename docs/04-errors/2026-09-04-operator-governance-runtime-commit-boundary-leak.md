# Operator Governance Runtime：事务提交边界泄漏

- 日期：2026-09-04
- 范围：Phase 2.10-II / Operator Governance / Trigger Invoke
- 类型：生产事务边界错误

## 现象

PostgreSQL Acceptance `test_operator_trigger_invoke_rolls_back_execution_idempotency_audit_trace_and_event_on_finalization_failure` 在最终 Audit 被模拟为失败后，发现 `OperatorActionIdempotency` 记录仍然存在。

上层 `OperatorActionGovernanceService.execute_trigger()` 明确调用 `WorkflowTriggerService.invoke(..., commit=False)`，并在最终治理失败时执行 `rollback()`；但此前 Runtime 完成阶段仍可能通过默认 `commit=True` 提交 Execution 事务，因此幂等记录已经脱离上层事务。

## 根因

事务提交边界只向下传播了一层：

```text
Operator Governance
    ↓ commit=False
WorkflowTriggerService.invoke
    ↓ commit=False
WorkflowExecutionService.run
    ↓ 未继续传播
WorkflowRuntime.execute
    ↓
Execution terminal transition commit=True
```

`WorkflowExecutionService.run()` 虽然已经支持 `commit` 参数，但调用 `WorkflowRuntime.execute()` 时没有继续传递该参数；同时 `WorkflowRuntime.execute()` 的终态 `transition()` 调用固定使用默认提交行为。

这形成了“上层延迟提交、Runtime 终态提前提交”的事务边界泄漏。

## 修复

1. `WorkflowExecutionService.run()` 将 `commit` 原样传递给 `WorkflowRuntime.execute()`。
2. `WorkflowRuntime.execute()` 增加 `commit` 参数，并将该参数传递给 DAG 与顺序执行两条路径的最终 `transition()`。
3. `commit=False` 时 Runtime 不得自行提交；Operator Governance 继续负责 Result Resource、Operator Action Idempotency、Audit、Trace 与 Integration Event 的统一最终提交。
4. 保留 `commit=True` 的默认行为，避免普通 Execution Runtime 调用行为发生不必要变化。

## 关联修复

Operator Action PostgreSQL 测试清理逻辑同时补充 `IntegrationEventRecord` 删除，避免治理测试在生成 Durable Integration Event 后因为 Tenant 外键残留导致清理失败。

## 防回归

现有 Manual Trigger Invoke 事务边界单元测试继续锁定 `commit=False` 从 Trigger Service 到 Execution Service 的传播；本次修复进一步锁定 Execution Service 到 Runtime 的传播，以及 Runtime 终态转换不提前提交。

## 本地验证要求

```powershell
cd backend
uv run pytest -q -W error tests/unit/services/trigger/test_service_transaction.py -s
uv run pytest -q -W error tests/integration/test_operator_action_idempotency.py tests/integration/test_operator_trigger_invoke.py -s
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\02_operator_trigger_invoke_acceptance.ps1
```

Gate 不自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis；缺少依赖时应按项目测试规则输出未执行状态与标准启动提示。

在获得新的本地执行结果前，不得将 PostgreSQL Acceptance 标记为已通过。
