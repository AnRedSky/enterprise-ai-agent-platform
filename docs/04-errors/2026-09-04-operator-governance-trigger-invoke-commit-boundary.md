# Manual Trigger Operator Invoke：事务提交边界错误

- 日期：2026-09-04
- 范围：Phase 2.10-II / Operator Governance / Trigger Invoke
- 类型：生产事务边界错误

## 现象

`OperatorActionGovernanceService.execute_trigger()` 为 Manual Trigger 调用 `WorkflowTriggerService.invoke(..., commit=False)`，期望 Trigger Invoke 的 Execution、Audit、Trace、Operator Idempotency 与最终治理 Audit 共享一个事务。

但 `WorkflowTriggerService.invoke()` 在创建 Execution 和写入 Trigger Audit/Trace 后，仍以默认参数调用 `WorkflowExecutionService.run()`。这会让 Runtime 使用 `commit=True` 提前提交事务，破坏 Operator Governance 的统一提交边界。

## 根因

`WorkflowTriggerService.invoke()` 已增加 `commit` 参数，但该参数只控制 Invoke 方法内部显式的 `db.commit()`，没有继续向下传递到 Execution Runtime。

因此出现“上层延迟提交、下层默认提交”的事务边界泄漏。

## 修复

将 `commit` 原样传递给 `WorkflowExecutionService.run(..., commit=commit)`。

这样：

- 普通 Trigger Invoke 使用 `commit=True` 时保持既有行为；
- Operator Governance 使用 `commit=False` 时，Execution Runtime 不得自行提交；
- Result Resource、Operator Action Idempotency、Audit、Trace 可以继续由治理服务统一最终化并提交；
- 任一最终化步骤失败时，治理层 rollback 可以覆盖整个事务。

## 防回归

新增单元测试锁定 `commit=False` 的传播：

`backend/tests/unit/services/trigger/test_service_transaction.py`

测试使用最小可控替身，不访问真实服务，不依赖人工身份或固定数据库数据。

## 验证

必须本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/unit/services/trigger/test_service_transaction.py -s
uv run pytest -q -W error tests/api_contract/test_api_operator_actions.py tests/api_contract/test_api_workflows_endpoints.py -s
$env:PYTHONTRACEMALLOC="25"
uv run pytest -q -W error -s
Remove-Item Env:PYTHONTRACEMALLOC -ErrorAction SilentlyContinue
uv run alembic upgrade head
```

真实 PostgreSQL Operator Governance Acceptance 应在上述 targeted/unit 验证后重新执行。未获得新的本地结果前，不得标记 Acceptance 已通过。
