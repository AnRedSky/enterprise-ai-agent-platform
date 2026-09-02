# ERR-0037：Operator Action 幂等成功状态被审计状态覆盖

## 现象

Phase 2.10-II 的 PostgreSQL Real Acceptance 在同一个 `Idempotency-Key` 第二次调用 Retry 时返回 HTTP 409：

> 相同 Idempotency-Key 的 Operator Action 已在处理中或此前失败

第一次 Retry 已经返回新的 `pending` Retry Execution，但随后持久化的 `OperatorActionIdempotency.status` 不是 `succeeded`，导致重放无法复用既有结果。

## 根因

`OperatorActionGovernanceService.execute_execution()` 在完成 `_finish_idempotency()` 后继续调用 `_audit(..., status="success")`。

`_audit()` 原实现把同一个 `status` 同时传给 Operator Action 持久事实与 `AuditLog`。因此 `_ensure_operator_action()` 会把已经完成的幂等事实从 `succeeded` 覆盖为 `success`。

两套状态语义实际不同：

- `OperatorActionIdempotency.status` 使用 `started / succeeded / failed`，用于幂等重放与结果资源判定。
- `AuditLog.status` 使用 `success` 等审计状态值，用于审计展示。

状态值混用破坏了幂等 Contract，而不是 Retry Execution 本身的业务状态错误。

## 修复

在 `_audit()` 内显式建立 Operator Action 状态与 Audit 状态的边界：

- `status == "success"` 映射为 Operator Action `succeeded`。
- `AuditLog.status` 继续保留原始 `success`。
- 失败状态继续按 Operator Action 的 `failed` 语义持久化。

该修复不改变租户边界、幂等键唯一约束或 Workflow Execution 状态机。

## 验证

必须执行：

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

随后执行 Phase 2.10-II Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
```

最后执行 Backend Regression Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

以上 Gate 只检查依赖服务状态，不自动启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis；测试数据由测试自动生成，无需手工填写。
