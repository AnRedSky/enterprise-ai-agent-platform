# 2026-08-27 Frontier Checkpoint Node Fact Conflict

## 问题

`frontier_completed` 在 Checkpoint Durable Write boundary 收紧为 Execution-level snapshot 后，旧的 Durable Frontier Worker 成功路径仍然把单 Node 的 `node_id`、`node_attempt`、`node_status` 与 `output_data` 传入 `frontier_completed` Checkpoint。

这会导致单 Node Frontier 在完成阶段被 Checkpoint boundary 拒绝，虽然 Node-level `node.completed` Checkpoint 已经由 `WorkflowExecutionService.transition_node()` 正确写入。

## 根因

两类 Durable Fact 的职责没有在 Frontier progression 调用侧同步收敛：

```text
node.completed
  = Node-level Durable Fact
  = 携带 node_id / attempt / status / output

frontier_completed
  = Execution-level Durable Fact
  = 只保存 merged / execution state
```

Frontier progression 仍沿用了旧的 Node Fact 参数，和新的 Durable Write Contract 冲突。

## 修复

`PlannerDrivenDurableFrontierWorkflowWorker` 的成功路径现在只向 `complete_frontier_with_checkpoint()` 提交 Execution-level `frontier_completed`：

```text
Frontier completion
  ├─ checkpoint_reason = frontier_completed
  ├─ node_id           = None
  ├─ node_attempt      = None
  ├─ node_status       = None
  └─ output_data       = None
```

单 Node 的详细完成事实继续由 `transition_node()` 在同一外层事务中写入 `node.completed` Checkpoint。

## 结果

```text
Node execution
    ↓
node.completed Checkpoint
    ↓
Frontier completion
    ↓
frontier_completed Execution Checkpoint
    ↓
Next Frontier
```

两种 Durable Fact 不再互相污染，同时保留原有 Frontier → Checkpoint → Next Frontier 原子事务边界。

## Unit Test

新增/调整 Frontier progression Unit Test，明确断言 `frontier_completed` 不得携带 Node Fact。

当前仍按开发准则暂停 Full Regression / E2E；本环境未执行 pytest，不记录为测试通过。