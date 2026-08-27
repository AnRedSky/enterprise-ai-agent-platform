# 2026-08-27 Multi-frontier Recovery Checkpoint Boundary

## 问题

`frontier_completed` 是 Multi-frontier / Durable Frontier 的 Execution-level Recovery 边界。若该类型 Checkpoint 同时携带 `node_id` 或 `node_status`，Recovery 会失去对“合并后的 Frontier state”与“单 Node Durable Fact”的边界区分。

## 风险

错误的 Checkpoint 形态可能被 Resume 当作合法快照继续复制 Node lineage，导致 Multi-frontier merged state 被错误解释为单 Node 完成事实，破坏 Replay 的语义闭包。

## 修复

Recovery Candidate Assessment 现在强制：

- `node.completed` 必须绑定 `node_id` 且 `node_status=completed`；
- `frontier_completed` 必须为 Execution-level Checkpoint，即 `node_id is None` 且 `node_status is None`；
- 两类 Checkpoint 都必须属于当前 Execution，并且产生时 `execution_status=running`。

## 边界

`frontier_completed` 的 `state_data` 继续作为 Durable Resume snapshot 使用，但不会被解释为某一个 Node 的完成事实。新的 Resume Execution 后续 Checkpoint sequence 独立于 Source Checkpoint sequence。

## 测试

已增加 Unit Test 覆盖携带 `node_id`、携带 `node_status` 的非法 `frontier_completed` Checkpoint。

当前阶段暂停完整 Regression / E2E；Unit Test 仅完成实现，未在当前 GitHub API 环境实际执行，因此不得标记为 PASS。
