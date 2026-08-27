# 2026-08-27 Checkpoint Worker Lease Write Guard

## 问题

Durable Frontier 已经在 Frontier terminal transition 层校验 Worker owner、Frontier attempt 与 Frontier lease；Progression 也会在写入 Checkpoint 前锁定关联 Execution 并校验 Execution worker owner / worker_attempt / lease。

但 Node-level `WorkflowExecutionCheckpointService.append_next_in_transaction()` 的 Worker fencing 过去只比较 `expected_worker_owner` 与 `expected_worker_attempt`。在 Execution owner 与 epoch 尚未被 Recovery 清理的窄并发窗口中，lease 已过期的 stale Worker 仍可能通过 owner + epoch 比较。

## 修复

带 `expected_worker_owner` / `expected_worker_attempt` 的 Checkpoint durable write 现在在锁定 `WorkflowExecution` 后必须同时满足：

```text
Execution.worker_owner == expected_worker_owner
AND
Execution.worker_attempt == expected_worker_attempt
AND
Execution.worker_lease_expires_at IS NOT NULL
AND
Execution.worker_lease_expires_at > now
```

任一条件失败均拒绝写入并抛出 409；调用方事务负责 rollback，因此不会留下新的 Checkpoint durable fact。

## 语义边界

- `Execution.worker_attempt` 是 Worker ownership epoch。
- `WorkflowFrontier.attempt` 是 Frontier consumption attempt。
- Checkpoint fencing 使用 Execution worker epoch，不使用 Frontier attempt。
- `frontier_completed` terminal Checkpoint 在 terminalization 前已经由 Frontier Progression 锁定并验证 Execution；终态后不再重复要求已经清除的 owner/lease。
- 不带 Worker fencing 参数的普通 Checkpoint API 保持原有通用语义，不强行引入 Worker lease 依赖。

## 验收要求

Unit Test 应覆盖：

1. owner 正确、epoch 正确、lease 有效 → 允许写入。
2. owner 错误 → 拒绝。
3. epoch 错误 → 拒绝。
4. lease 为空 → 拒绝。
5. lease 已过期 → 拒绝。
6. rejection 发生在 flush/commit 前，外层事务可以完整 rollback。

本轮按开发策略未执行 pytest；不得将未执行测试记录为 PASS。
