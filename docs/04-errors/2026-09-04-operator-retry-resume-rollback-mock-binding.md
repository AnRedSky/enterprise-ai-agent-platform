# 2026-09-04 Operator Retry / Resume 回滚验收 Mock 绑定错误

## 1. 现象

PostgreSQL Operator Governance Gate 的 Retry / Resume cross-session concurrency 验收中，2 个回滚测试失败：

- `test_retry_rolls_back_execution_and_governance_facts_when_finalization_fails`
- `test_resume_rolls_back_execution_and_governance_facts_when_finalization_fails`

失败异常：

```text
TypeError: _raise_after_audit() missing 1 required positional argument: 'service'
```

## 2. 根因

测试通过 `AsyncMock(side_effect=_raise_after_audit)` 替换实例方法 `_audit` 时，`AsyncMock` 调用 `side_effect` 不会自动把被替换实例 `service` 作为第一个参数传入。

原辅助函数签名要求显式 `service` 参数，因此 Mock 实际执行时只有 `_audit` 的业务参数，导致参数绑定失败，测试甚至没有进入“真实 Audit 已写入当前事务后再故意失败”的回滚验证路径。

## 3. 修复

使用 `functools.partial(_raise_after_audit, service)` 显式绑定被测 Service 实例，再交给 `AsyncMock.side_effect`。

修复后的语义保持不变：

1. 调用正式 `OperatorActionGovernanceService._audit` 写入 AuditLog；
2. 在同一数据库事务内主动抛出 `RuntimeError`；
3. 验证 Operator Execution、Idempotency、AuditLog、WorkflowTraceEvent 均随最终化失败一起回滚。

## 4. 防回归

本地应重新执行：

```powershell
cd backend
$env:RUN_DATABASE_INTEGRATION="1"
uv run pytest -q -W error tests/integration/test_operator_execution_retry_resume_concurrency.py -s
```

随后执行完整 PostgreSQL Operator Governance Acceptance：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
```

本 Gate 不自动启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis，也不要求手工填写测试数据。

## 5. 结论

该问题属于测试 Mock 绑定错误，不是 Operator Governance 生产事务边界错误。修复后必须以实际本地 PostgreSQL 验收结果作为最终结论。
