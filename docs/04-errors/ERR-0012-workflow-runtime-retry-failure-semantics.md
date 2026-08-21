# ERR-0012 Workflow Runtime Retry Failure Semantics

## 现象

1.9-C Real API Reliability 场景进入真实 HTTP bootstrap 时，Workflow Execution Runtime 将节点超时、retry budget 耗尽及 deadline backoff 边界中的原始异常错误地收敛为 `HTTP 500 Workflow Runtime 执行失败`。对应单元测试出现 7 个失败；Real API retry deadline fixture 进一步表现为预期 `504 WORKFLOW_TIMEOUT` 未能稳定得到。

## 根因

- Runtime 在 retry exhaustion 后重新构造 `ConnectionError` / `TimeoutError`，丢失了实际失败异常及其类型语义。
- `WorkflowExecutionService.run()` 的兜底 `except Exception` 会把 transport/timeout 异常再次包装为通用 500。
- Runtime retry/deadline 边界需要在“节点失败 → retry budget → backoff → workflow deadline”之间保持明确的错误分类，而不能用通用 Runtime Error 覆盖。

## 修复

- Runtime 保存本次节点失败的原始异常，在 retry policy / node attempts / retry budget 耗尽时优先保留 `HTTPException`、`ConnectionError`、`TimeoutError` 的类型语义。
- `WorkflowExecutionService.run()` 对 transport/timeout 异常单独处理，先将 Execution 持久化为 failed 并记录对应 `error_code`，再重新抛出原始异常。
- `HTTP 504` 仍统一映射为 `WORKFLOW_TIMEOUT`，deadline backoff 超过剩余 workflow deadline 时直接返回 504，不继续启动下一次 retry。

## 验证要求

本错误修复必须在开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_runtime_timeout.py tests/unit/test_workflow_execution_retry_transition.py tests/unit/test_workflow_retry_budget.py tests/unit/test_workflow_retry_policy.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

实际通过/失败结果以本地执行输出为准，不在文档中预填通过状态。
