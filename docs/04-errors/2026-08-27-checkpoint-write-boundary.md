# 2026-08-27 Checkpoint Write Boundary

## 问题

Recovery 层已经能够拒绝非法 `frontier_completed` Checkpoint，但此前 Checkpoint Durable Write 本身仍允许调用方把 Node Fact 填入 Execution-level Checkpoint。

这意味着非法快照可能先落库，再在 Recovery 阶段才被发现，违反 Durable Fact 写入边界应尽早失败的原则。

## 修复

`WorkflowExecutionCheckpointService` 在 `_build()` 与 `append_next_in_transaction()` 两个写入入口统一增加 boundary validation：

```text
frontier_completed
  ├─ node_id       == None
  ├─ node_attempt  == None
  └─ node_status   == None
```

同时：

```text
node.completed
  └─ node_id != None
```

因此 Node-level 与 Execution-level Checkpoint 在持久化入口即被严格区分。

## 结果

```text
Runtime / Worker
      ↓
Checkpoint Durable Write
      ↓
Boundary Validation
      ├── Node Fact
      └── Execution Fact
      ↓
PostgreSQL
      ↓
Recovery / Replay
```

Recovery 不再承担“发现已经写入的非法 Checkpoint”这一职责，而只消费已经满足 Durable Fact Contract 的快照。

## 验证

新增 Unit Test：

- `frontier_completed + node fact` 必须拒绝；
- 合法 `frontier_completed` 必须保持纯 Execution-level；
- `node.completed` 缺少 `node_id` 必须拒绝。

当前仍按开发准则暂停 Full Regression / E2E；本环境无法直接执行 pytest，因此不伪造测试通过结果。
