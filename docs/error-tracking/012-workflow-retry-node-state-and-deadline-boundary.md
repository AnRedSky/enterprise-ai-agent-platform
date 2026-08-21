# 012 — Workflow Retry Node State / Deadline Boundary

## 现象

Real API 与 backend pytest 暴露两组运行时边界问题：

1. Retry 第一次失败后，下一次 Runtime attempt 没有显式执行 `failed -> running`，导致真实数据库状态机可能在下一次失败时出现 `Node 不允许从 failed 到 failed`，并造成 retry fixture bootstrap 失败。
2. Retry backoff 如果已经跨越 Workflow deadline，Runtime 仍记录 `node.retry.scheduled`，没有记录 `node.retry.exhausted`，也没有以 `WORKFLOW_TIMEOUT` 结束 Execution。

## 根因

`WorkflowExecutionService.run()` 在 `node_execution` 第一次进入 `running` 后，retry loop 只 sleep，再次直接调用 `WorkflowRuntime.execute_node()`；Node 状态没有回到 `running`。

同时 retry schedule 阶段只计算 delay，没有比较剩余 workflow deadline。

## 修复

- retry sleep 完成后显式调用 `transition_node(..., "running")`，由状态机负责 attempt +1；
- 在记录 `node.retry.scheduled` 前计算剩余 deadline；
- 当 `delay >= remaining` 时直接记录 `node.retry.exhausted`，`reason=workflow_deadline`；
- Execution 以 `WORKFLOW_TIMEOUT` / HTTP 504 结束；
- same-slot Circuit Breaker fast-fail 不再被 retry 状态污染。

## 回归验证

新增 unit contract：

- `backend/tests/unit/test_workflow_execution_retry_transition.py`

本地建议执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Real API 必须确认：

- retry fixture bootstrap 正常；
- Circuit Breaker fast-fail 第二 Execution 的 node `attempt == 1`；
- retry deadline fixture 返回 HTTP 504 且 `error_code=WORKFLOW_TIMEOUT`；
- 同一 scheduled interval slot 不产生重复 Execution。
