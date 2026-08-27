# 2026-08-27 Durable Frontier Completion Source Binding

## 问题

`frontier_completed` Checkpoint 只通过 `execution_id + checkpoint_reason` 查询时，多个并行 Frontier 属于同一 Execution 的情况下，最新 completion Checkpoint 可能属于另一个 Frontier。这样重复 completion 无法证明当前 Frontier 对应的 Durable fact，可能错误接受或拒绝幂等请求。

## 修复

为 `WorkflowExecutionCheckpoint` 增加可空 `frontier_id`，并建立到 `workflow_frontiers.id` 的外键与索引。

`frontier_completed` 写入现在必须绑定 source Frontier；普通 Node / Execution Checkpoint 不得设置 `frontier_id`。

重复 completion 查询改为：

```text
Execution
  + source Frontier
  + frontier_completed
      ↓
exact Durable Checkpoint
```

不再按 Execution 下最新的 `frontier_completed` 猜测来源。

## 兼容策略

历史 Checkpoint 的 `frontier_id` 保持 NULL，不进行启发式回填。旧 Frontier 若缺少可证明的 source binding，重复 completion 会被视为不完整 Durable lifecycle 并拒绝收敛，而不是猜测错误事实。

## 单元测试

新增 `backend/tests/unit/test_frontier_checkpoint_binding.py`，覆盖 source Frontier 绑定、duplicate completion 精确查询、frontier_completed 必须绑定 Frontier，以及 ORM 外键声明。

本轮仅实现 Unit Test，未执行 pytest。
