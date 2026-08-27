# Phase 2.7 Checkpoint Boundary Closure Addendum

> 基线：`main`
> 日期：2026-08-27
> 范围：Durable Frontier → Checkpoint → Next Frontier

## 1. 本轮修复

在 `frontier_completed` 收紧为 Execution-level Durable Fact 后，发现 Durable Frontier Worker 成功路径仍向该 Checkpoint 传递单 Node Fact 字段。

修复后明确分层：

```text
Node 执行完成
    ↓
node.completed Checkpoint
    ├─ node_id
    ├─ node_attempt
    ├─ node_status
    └─ output_data

Frontier 完成
    ↓
frontier_completed Checkpoint
    ├─ node_id      = None
    ├─ node_attempt = None
    ├─ node_status  = None
    └─ output_data  = None
```

两类事实继续共享同一外层事务，但职责不可混合。

## 2. Durable Recovery 语义

单 Node Frontier 不需要重复写 Node-level Fact：`WorkflowExecutionService.transition_node()` 已在当前 Worker ownership / fencing generation 下写入 `node.completed`。

Frontier progression 只负责：

```text
Frontier fencing
    ↓
Execution-level frontier_completed Checkpoint
    ↓
Next Frontier 幂等入队
```

Multi-frontier 在所有 Branch 完成后使用 merged state 创建 Execution-level `frontier_completed` Checkpoint，随后由 Planner 生成 Join Frontier。

## 3. Recovery / Join

恢复时 Source of Truth 仍为 PostgreSQL Durable Node / Checkpoint facts：

```text
Durable Node facts
      ↓
唯一 DAG Planner
      ↓
Join frontier
      ↓
merged predecessor state
      ↓
Join Node
```

不得使用 Trace event 或内存 Branch output 替代 Durable Fact。

## 4. Unit Test

Frontier progression Unit Test 已明确验证：

- `frontier_completed` 不携带 `node_id`；
- 不携带 `node_attempt`；
- 不携带 `node_status`；
- 不携带 `output_data`；
- Worker owner / attempt fencing 参数仍必须传递。

当前按开发策略暂停 Full Regression、Real API 与 E2E；本环境未执行 pytest，因此不记录为通过。