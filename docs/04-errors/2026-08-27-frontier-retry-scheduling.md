# 2026-08-27 Durable Frontier Retry Scheduling

## 背景

Durable Frontier 已完成持久化、Claim、lease fencing、过期恢复以及 Scheduled Trigger / Worker 接入。下一主线要求将可重试失败转换为持久化 retry work，而不是在 Worker 内存中 sleep 或重新创建 WorkflowExecution。

## 本轮实现

- 新增 `FrontierRetryPolicy`；
- retry 使用当前 Frontier 的 `attempt` 作为 fencing generation；
- 指数退避：`base_delay * 2^(attempt-1)`，并由 `max_delay_seconds` 上限约束；
- 可重试时：当前 Frontier → `retry_wait`，写入 `available_at` 和 error facts；
- 下一次成功 Claim 才增加 `attempt`，因此 recovery/retry scheduling 本身不会提前消耗 fencing generation；
- 达到 `max_attempts` 时，同一 Frontier → `failed`；
- 不创建新的 WorkflowExecution，也不创建第二个 Frontier；
- 通过既有 `transition_owned_frontier()` 强制 `worker_owner + attempt` ownership/fencing 校验；
- Retry primitive 不执行 commit，由外层 Scheduler/Worker 事务统一提交。

## 当前边界

本轮只建立 Durable Retry Scheduling domain primitive 和 Unit Test Contract。Runtime 的具体错误分类仍由现有执行层负责，不能把所有 `failed` 自动视为可重试；后续 Worker integration 必须先接入明确的 retryable error classification，再调用 `schedule_frontier_retry()`。

## 测试边界

已新增 Unit Test 覆盖 policy/backoff、配置校验、同一 Frontier retry、attempt exhausted terminal failure。当前环境无法实际执行 pytest，因此不记录 PASS；完整回归、E2E、Real API 继续暂停。
