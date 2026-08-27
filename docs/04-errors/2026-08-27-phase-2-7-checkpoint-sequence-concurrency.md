# Phase 2.7 Checkpoint 序号并发分配问题

- 日期：2026-08-27
- 阶段：Phase 2.7-A Durable Recovery Closure
- 类型：Durable Checkpoint / 并发一致性

## 问题

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 原先通过 `MAX(sequence) + 1` 计算下一个 Checkpoint 序号，但在两个 Worker 同时处理同一 Execution 时，两边可能读取到相同的最大序号并计算出相同的下一序号。

数据库虽然通过 `(execution_id, sequence)` 唯一约束阻止重复数据，但这只能在冲突发生后失败，不能作为正常的序号分配机制，也可能让 Recovery 写入路径出现不必要的事务失败。

## 根因

原流程：

```text
Worker A ─┐
          ├─ MAX(sequence) = N ─→ N + 1
Worker B ─┘
```

两个事务没有在读取最大序号前建立同一 Execution 的串行化边界。

## 修复

现在在当前数据库事务中先对 `workflow_executions` 对应行执行 `SELECT ... FOR UPDATE`，确认 Execution 存在后，再读取该 Execution 的最大 Checkpoint 序号并生成 `N + 1`。

```text
锁定 Execution 行
      ↓
读取 MAX(sequence)
      ↓
计算下一序号
      ↓
写入 Checkpoint
      ↓
flush
```

同一 Execution 的并发 Checkpoint 序号分配因此由数据库行锁串行化。

## 边界

- 只锁定当前 Execution，不扩大为全局锁。
- 该方法仍然只 `flush`，提交边界继续由外层事务负责。
- `append()` 的显式序号写入语义保持不变。
- 本修复不改变 Checkpoint 数据模型，不需要新增 migration。
- Worker ownership、Recovery 调度和状态机推进仍不属于 Checkpoint Service 职责。

## 测试

新增 `backend/tests/unit/test_workflow_checkpoint_sequence_allocation.py`，覆盖：

1. 自动分配序号前必须锁定 Execution；
2. 读取当前最大序号后生成下一个序号；
3. 不存在的 Execution 不允许产生孤立 Checkpoint。

按照当前开发策略，本阶段暂停完整 Regression / Real API / E2E Gate；实际 Unit Test 结果以开发者本地执行为准，未执行不得标记为通过。
