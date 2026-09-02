# Phase 2.10-II / II-09 — Operator Action Result Lineage

## 1. 目标

在 Runtime Correlation 已能够表达完整 Audit Fact 后，继续闭合核心运维链：

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

本切片以 `Retry` 为代表性 Operator Action，直接调用正式 `OperatorActionGovernanceService`，在真实 PostgreSQL 中验证最终持久化事实，不通过测试复制生产算法。

## 2. Backend 实现范围

- 自动生成 Tenant、User、Workflow、Published WorkflowVersion、failed WorkflowExecution 与 Idempotency-Key；
- 调用正式 `OperatorActionGovernanceService.execute_execution(..., action="retry")`；
- 验证 Operator Action 幂等记录为 `succeeded`；
- 验证 `result_resource_type/result_resource_id` 指向新建 Retry Execution；
- 验证 Operator Audit 指向原始资源并通过 `workflow_execution_id` 指向结果 Execution；
- 验证 Audit 的 Trace 标识、结果 Execution 的 `execution.created` Trace 事实；
- 调用正式 `RuntimeAuditTraceCorrelationService.by_operator_action()` 验证最终关联视图。

不新增数据库字段，不新增平行 Service，不绕过既有 Workflow Execution 生命周期。

## 3. 自动化 Gate

新增：

```text
backend/scripts/test/phase-2.10/25_operator_action_result_lineage_gate.ps1
```

执行顺序：

1. Runtime Correlation API Contract；
2. PostgreSQL readiness `SELECT 1`；
3. Real PostgreSQL Operator Action Result Lineage Acceptance；
4. 受保护服务进程边界检查。

Gate 只探测 PostgreSQL，不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。该边界与 `docs/01-governance/DEVELOPMENT.md` 的服务依赖规则一致。

## 4. 本地执行

```powershell
cd backend

uv run pytest -q -W error tests/api_contract/test_runtime_correlations_contract.py

uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1

uv run pytest -q -W error
```

Real PostgreSQL 测试会自动生成并清理全部测试身份、资源和幂等键，不要求手工填写 ID、Token 或业务数据。

## 5. 完成判定

- Contract 测试必须通过且 warnings 视为错误；
- Real PostgreSQL Acceptance 必须通过；
- Operator Action → Audit → Result Resource → Execution/Trace 必须能够完整回溯；
- Gate 运行期间不得出现受保护服务的新进程；
- 最终 Backend Regression 以开发者本地实际执行结果为准。
