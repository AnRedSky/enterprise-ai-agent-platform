# Phase 2.7 — Checkpoint Durable Fact Completeness

- 日期：2026-08-27
- 阶段：Phase 2.7-A Conditional Branching Durable Recovery Closure
- 严重级别：High

## 问题

带 Node 的 `WorkflowExecutionCheckpoint` 同时保存 `node_id`、`node_attempt`、`node_status`、`output_data`，但 Recovery 读取 Checkpoint 时，如果不验证对应 `WorkflowNodeExecution`，就可能将不同时间边界的 Node fact 与 Checkpoint snapshot 拼接使用。

这会破坏 Durable Recovery 的基本不变量：Planner 必须从同一持久化事实边界重建 frontier。

## 修复

`WorkflowExecutionCheckpointService.assert_node_fact_complete()` 现在提供显式完整性 Contract：

```text
Checkpoint(node_id)
      ↓
对应 WorkflowNodeExecution
      ↓
node_id 一致
status 一致
attempt 一致
output_data 一致
      ↓
允许作为 Durable Node Fact
```

Execution-level Checkpoint（`node_id=None`）不要求 NodeExecution。

`latest_recovery_fact()` 读取最新 Checkpoint 后执行该校验，校验失败立即抛出 `ValueError`，不允许 Recovery 静默继续。

## 设计边界

- Checkpoint Service 只负责持久化事实与事实完整性校验；
- 不负责 Worker ownership / fencing；
- 不负责 Recovery 调度；
- 不把 Trace 当作业务状态源；
- 不新增第二套 DAG Planner。

## 后续

继续验证 checkpoint sequence、NodeExecution facts 与 Recovery Planner 使用的 snapshot 是否存在统一边界，并在此基础上完成 Conditional Decision 可重建性与 Trace lineage Closure。
