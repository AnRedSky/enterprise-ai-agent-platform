# Operator Action Result Lineage 事务边界

## 1. 问题

Phase 2.10-II / II-09 的 Retry Operator Action 需要同时收敛：

```text
Operator Action
  ↓
Idempotency Result Resource
  ↓
AuditLog
  ↓
Workflow Execution
  ↓
Workflow Trace
```

如果 Workflow Execution Retry 在 Governance Service 写入 Result Resource / Operator Audit 之前提交，后续持久化失败就可能留下已提交 Retry Execution，而 Operator Action 幂等事实仍处于 `started`，形成半提交治理链。

## 2. 根因

`WorkflowExecutionService.retry()` 原本承担自己的事务提交边界，而 `OperatorActionGovernanceService.execute_execution()` 还需要继续写入 Operator Action 幂等结果和 Operator Audit。两个 Service 的职责边界导致一次业务动作被拆成多个提交阶段。

同一问题需要同步审查 Durable Resume：Operator Governance Resume 也必须在 Result Resource、Operator Audit 和 Trace 事实完成前禁止提前提交。

## 3. 修复原则

- `WorkflowExecutionService.retry()` 支持 `commit` 参数，默认 `True`，保持直接调用方行为兼容；
- `WorkflowExecutionService.resume_from_latest_checkpoint()` 使用同一可控提交边界；
- Operator Governance 的 Retry / Resume 调用统一使用 `commit=False`；
- Governance Service 在 Result Resource、Audit 与 Trace 全部完成后统一 `commit()`；
- 失败路径不得把已经创建的 Retry Execution 作为已提交事实留下；
- tenant boundary、Idempotency-Key 冲突和并发语义保持不变；
- 测试不复制生产算法，不手工填写业务 ID、Token 或 Idempotency-Key。

## 4. 验证

新增真实 PostgreSQL 回滚验收：

```text
backend/tests/api_real/test_operator_action_transaction_rollback_acceptance.py
```

该测试模拟最终 Operator Audit 写入失败，并验证：

1. Retry Execution 不存在已提交记录；
2. Operator Action Idempotency 记录不留下半成品；
3. Operator Audit 不存在；
4. Retry Execution 对应的 Trace 不存在。

现有 Result Lineage Gate 已纳入该回滚测试，并保持：

- 不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；
- PostgreSQL 仅做 readiness 检查；
- 测试身份、业务资源与幂等键自动生成并清理；
- Python warnings 使用 `-W error`。

## 5. 本地验收顺序

```powershell
cd backend

uv run pytest -q -W error tests/api_contract/test_runtime_correlations_contract.py
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
uv run pytest -q -W error tests/api_real/test_operator_action_transaction_rollback_acceptance.py -m real_api

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1

uv run pytest -q -W error
```

只有开发者本地实际执行结果完成后，才更新 Phase Acceptance / Project Status 为通过；本记录本身不预填通过结果。
