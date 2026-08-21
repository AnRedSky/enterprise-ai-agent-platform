# ERR-0021 — Real API Retry Fixture 未提供 retry budget 且缺少 retry scheduled trace

## 现象

Real API Governance Gate 中，node retry fixture 的 Node Execution `attempt` 保持为 1；Circuit Breaker Open fixture 缺少 `node.retry.scheduled` governance trace。

## 根因

1. Node `max_attempts=2` 不能绕过 Workflow `retry_budget.max_retries`；fixture 未配置 retry budget 时默认值为 0，因此第一次失败直接结束。
2. Runtime 在进入下一次 Node attempt 前没有记录 `node.retry.scheduled` trace，只有状态变化 trace。

## 修复

1. Real API retry governance fixture 显式设置 `retry_budget.max_retries=1`。
2. `WorkflowExecutionService.transition_node()` 在 `failed -> running` 的重试状态转换时记录 `node.retry.scheduled`，并携带 attempt。

## 验证

需要重新运行本地 unit retry tests 和完整 Real API Gate；在测试全部通过前不得将 Phase 1.9-C 标记为完成。
