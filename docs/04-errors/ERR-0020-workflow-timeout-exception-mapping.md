# ERR-0020 — Workflow node timeout 被错误暴露为内部 TimeoutError

## 状态

**Resolved in code — 等待开发者本地验证。**

## 发现阶段

Phase 1.9-C Real API Reliability / Workflow Runtime focused tests。

## 现象

本地专项测试中：

```text
tests/unit/test_workflow_runtime_timeout.py::test_run_marks_workflow_timeout_as_failed
```

执行结果为 `500`/裸 `TimeoutError`，而测试契约要求 Workflow Runtime timeout 以 HTTP 504 暴露，并将 Execution 标记为 failed。

## 根因

`WorkflowRuntime.execute()` 在 node timeout 分支将 `NODE_TIMEOUT` 重新抛出为 `asyncio.TimeoutError`。在 Python 3.12 中该异常与内置 `TimeoutError` 等价，`WorkflowExecutionService.run()` 的通用 timeout 捕获路径会把它重新作为底层异常抛出，而不是形成 API 层约定的 HTTP 504。

## 修复

`WorkflowRuntime.execute()` 对已经分类为 `NODE_TIMEOUT` 且耗尽 retry policy / retry budget 的情况直接抛出：

```python
HTTPException(504, error_message)
```

`WORKFLOW_TIMEOUT` 原有 504 行为保持不变。

## 验证要求

必须由开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_runtime_timeout.py tests/unit/test_workflow_execution_retry_transition.py tests/unit/test_workflow_retry_budget.py tests/unit/test_workflow_retry_policy.py
```

并继续执行完整 Real API Gate。