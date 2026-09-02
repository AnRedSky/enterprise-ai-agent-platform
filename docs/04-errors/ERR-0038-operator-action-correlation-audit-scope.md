# ERR-0038：Operator Action 反查 Audit 范围混入 Execution 生命周期审计

## 现象

Phase 2.10-II 的 PostgreSQL Real Acceptance 在通过 `RuntimeAuditTraceCorrelationService.by_operator_action()` 反查 Retry Operator Action 时失败：

```text
assert correlation["audits"]["total"] == 1
E assert 2 == 1
```

数据库中实际只有 1 条直接关联当前 `operator_action_id` 的 Operator Audit，但反查结果同时返回了 Retry Execution 的生命周期 Audit，因此聚合数量变成 2。

## 根因

`RuntimeAuditTraceCorrelationService.by_operator_action()` 已经根据 Operator Action 的 `result_resource_id` 定位到结果 Workflow Execution，但随后调用 `_paged_audits()` 时同时传入了 `execution_id` 与 `operator_action_id`。

`_paged_audits()` 的组合语义是：

- `execution_id`：查询该 Execution 的生命周期 Audit，并兼容通过 Trace ID 恢复历史 Audit；
- `operator_action_id`：查询直接挂接当前 Operator Action 的 Audit。

两个条件同时存在时采用 OR 关系，因此 Operator Action 反查会得到“Execution 生命周期 Audit + 当前 Operator Audit”，与 `by_operator_action()` 的聚合语义不一致。

## 修复

保留 `by_operator_action()` 对结果 Execution 的查询，用于返回：

- Result Execution；
- Execution Trace；
- 与该 Execution 关联的 Operator Actions。

但该入口的 `audits` 改为仅使用 `operator_action_id` 查询，不再同时传入 `execution_id`。因此：

- `by_execution()` 保持完整 Execution 生命周期 Audit 查询语义；
- `by_operator_action()` 保持当前 Operator Action 的直接 Audit 反查语义；
- tenant boundary、分页、Audit action/status 过滤和现有持久化事实均不改变。

## 验证

本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

随后执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
```

最后执行 Backend Regression：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Gate 只检查依赖服务状态，不自动启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis；测试上下文由测试自动生成，无需手工填写测试数据。
