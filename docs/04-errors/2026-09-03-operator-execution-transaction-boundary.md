# Phase 2.10-II：Operator Execution 事务边界

## 1. 问题

`OperatorActionGovernanceService.execute_execution()` 已经具备统一的 Operator Idempotency、Audit 与最终 `commit()`，但 `run()` 与 `cancel()` 仍使用 Execution 领域服务的默认 `commit=True`。

这会导致 Execution 状态可能先于 Operator Action Audit / 幂等事实提交，形成“业务状态已提交、治理事实未提交”的半提交窗口；`retry()` 与 `resume()` 已使用 `commit=False`，因此三类 Execution Action 的事务语义不一致。

## 2. 根因

Execution 领域服务既支持状态变更，也保留默认立即提交以兼容普通调用方。Operator Governance 是更高层的事务协调者，必须显式关闭领域服务内部提交，把状态变更、Operator Idempotency、Audit 和最终提交放入同一治理事务。

## 3. 修复

- `execute_execution(run)` 改为调用 `WorkflowExecutionService.run(..., commit=False)`。
- `execute_execution(cancel)` 改为调用 `WorkflowExecutionService.cancel(..., commit=False)`。
- 保留 `retry()` / `resume()` 的 `commit=False` 语义。
- 新增单元测试验证 `run/cancel` 的 commit 边界，以及 Audit 失败时不会由 Governance 主动提交。

## 4. 边界

`commit=False` 只约束 Operator Governance 调用的 Execution 领域事务边界；Workflow Runtime 内部 Durable Node / Checkpoint 持久化仍可使用其既有独立提交边界，不能将两者误认为同一事务。

## 5. 本地验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py
uv run pytest -q -W error tests/unit tests/integration -m "unit or integration" --tb=long
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Real API Gate 当前用户反馈结果为 `78 passed, 1 skipped, 2 deselected`；上述新增事务测试尚未在用户本地实际执行，因此不得预填为通过。
