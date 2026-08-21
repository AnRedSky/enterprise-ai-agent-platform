# ERR-0020 — Workflow 504 错误码丢失 Node Timeout 语义

## 现象

Workflow Runtime 已将节点超时转换为 HTTP 504，但 `WorkflowExecutionService.run()` 将所有 504 统一持久化为 `WORKFLOW_TIMEOUT`，导致节点超时测试期望的 `NODE_TIMEOUT` 被覆盖。

## 根因

HTTP 504 同时用于节点超时和 Workflow deadline/backoff 超时；Execution Service 原实现没有区分两种语义。

## 修复

`WorkflowExecutionService.run()` 根据 Runtime 返回的 504 detail 区分：节点执行超时保存为 `NODE_TIMEOUT`，Workflow deadline/backoff 超时保存为 `WORKFLOW_TIMEOUT`。

## 验证

需要本地执行 `tests/unit/test_workflow_runtime_timeout.py` 等专项测试，并通过 Real API Gate 后再关闭本错误记录。
