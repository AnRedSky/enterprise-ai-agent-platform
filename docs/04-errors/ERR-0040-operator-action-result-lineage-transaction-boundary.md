# ERR-0040：Operator Action Result Lineage 两阶段提交边界

## 1. 现象

Retry Operator Action 在 `WorkflowExecutionService.retry()` 内部提前提交 Retry Execution 及其基础 Audit/Trace，随后 `OperatorActionGovernanceService.execute_execution()` 才写入 Operator Action Result Resource 与最终 Operator Audit。

如果后续 Result Resource 或 Operator Audit 写入失败，数据库可能已经存在 Retry Execution，而 Operator Action 幂等事实尚未完成，形成半提交治理链。

## 2. 根因

领域 Service 与 Operator Governance 共用一个 `AsyncSession`，但 `retry()` 自己执行 `commit()`，导致上层无法继续控制完整 Result Lineage 的事务边界。

## 3. 修复

`WorkflowExecutionService.retry()` 增加 `*, commit: bool = True`：

- 默认 `True`，保持现有直接调用方兼容。
- Operator Governance Retry 使用 `commit=False`。
- Resume 路径已经支持 `commit` 参数，Operator Governance Resume 同样显式使用 `commit=False`。
- Governance 在 Result Resource、Operator Action、Audit 全部 flush 成功后统一 commit。
- 最终 Operator Audit 失败时，不执行 commit，由当前事务关闭路径回滚 Retry Execution、Operator Action Idempotency、Audit 与 Trace。

## 4. 回滚验收

新增：

`backend/tests/api_real/test_operator_action_transaction_rollback_acceptance.py`

测试模拟最终 Operator Audit 失败，并验证：

- Retry Execution 不存在；
- Operator Action Idempotency 不存在；
- Operator Audit 不存在；
- Retry 新增 Trace 不存在；
- 原始 failed Execution 保留。

## 5. 验证顺序

```powershell
cd backend

uv run pytest -q -W error tests/unit -m "not real_api"

uv run pytest -q -W error `
  tests/api_real/test_operator_action_result_lineage_acceptance.py `
  tests/api_real/test_operator_action_transaction_rollback_acceptance.py `
  -m real_api

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_backend_regression_gate.ps1
```

## 6. 约束

- 保持 tenant boundary、Idempotency-Key 冲突和并发安全语义。
- 不自动启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。
- warnings-as-errors 保持开启。
- 测试数据、身份与 Idempotency-Key 均自动生成。
