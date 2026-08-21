# ERR-0019 — Workflow Runtime Retry Failure Semantics

## 1. 发现阶段

Phase 1.9-C — Real API Reliability Scenarios。

## 2. 现象

开发者本地针对 1.9-B Runtime timeout/retry boundary 执行专项测试时出现 7 个失败，主要表现为：

- workflow timeout 预期 HTTP 504，实际 HTTP 500；
- retry budget / retry deadline 预期保留原始 `ConnectionError` 或 HTTP 503，实际被包装为通用 `Workflow Runtime 执行失败`；
- Real API retry deadline fixture 预期 HTTP 504 `WORKFLOW_TIMEOUT`，实际出现 provider HTTP 404。

## 3. 根因判断

`WorkflowRuntime.execute()` 在 retry policy、node attempts 或 retry budget 耗尽后重新构造异常，导致原始 transport/timeout/HTTP failure 语义丢失；`WorkflowExecutionService.run()` 的通用 `except Exception` 又把 transport/timeout 异常二次包装为 HTTP 500。

此外，workflow deadline 是跨整个执行的单一时间预算，retry backoff 超过剩余 deadline 时必须在下一次 runtime call 之前终止，而不能让 provider failure 覆盖 deadline 结果。

## 4. 修复

- Runtime 保存当前节点的原始异常，在 retry exhaustion 时优先重新抛出原始 `HTTPException`、`ConnectionError`、`TimeoutError`。
- `WorkflowExecutionService.run()` 对 transport/timeout 异常单独持久化 failed/error_code 后重新抛出，不再统一包装成 500。
- retry backoff 在 sleep 前重新计算 workflow remaining deadline；backoff 超出剩余预算直接返回 HTTP 504 / `WORKFLOW_TIMEOUT`。
- deadline、retry budget、node max attempts 继续保持独立边界。

## 5. 验证要求

本记录不预填测试 PASS。必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_runtime_timeout.py tests/unit/test_workflow_execution_retry_transition.py tests/unit/test_workflow_retry_budget.py tests/unit/test_workflow_retry_policy.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

结果以实际执行输出为准。
