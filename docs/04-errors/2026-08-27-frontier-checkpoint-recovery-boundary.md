# 2026-08-27 Frontier Checkpoint Recovery Boundary

## 问题

Durable Frontier Worker 成功路径使用 `checkpoint_reason="frontier_completed"` 写入统一 Progression Checkpoint，而 Recovery Candidate 原先只接受 `checkpoint_reason="node.completed"`。

因此 Multi-frontier / Execution-level Checkpoint 虽然已经持久化，却可能被 Automatic Recovery 判定为不可恢复。

## 修复

`WorkflowExecutionCheckpointRecoveryService` 现在明确支持两个 Resume 边界：

```text
node.completed
    → 必须绑定 node_id + node_status=completed

frontier_completed
    → 可以是 Execution-level Checkpoint
    → 用于 Multi-frontier merged state
```

两者都必须满足：

```text
Checkpoint.execution_status == running
Source Execution.status == failed
Worker ownership == None
```

## 设计意图

Recovery 不再假设“每一个可恢复 Checkpoint 都必须绑定单 Node”。这是因为 Durable Frontier 的统一 Progression primitive 已经允许：

```text
Single Node
  → Node-level Checkpoint

Multi-frontier
  → Execution-level merged Checkpoint
```

恢复边界必须与生产成功路径的实际 Checkpoint Contract 保持一致，而不是复制一套旧的 Node-only 判断。

## Unit Test

新增覆盖：

- `node.completed` 可恢复；
- `frontier_completed` Execution-level Checkpoint 可恢复；
- running Execution 拒绝；
- 活跃 Worker ownership 拒绝；
- 缺失 / 非法 Checkpoint 拒绝。

当前环境未实际执行 pytest，因此不记录 Unit Test PASS。