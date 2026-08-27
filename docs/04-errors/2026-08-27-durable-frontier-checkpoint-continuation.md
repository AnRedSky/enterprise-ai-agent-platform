# Durable Frontier Checkpoint Continuation

## 问题

Durable Resume Runtime 已实现 completed Node 过滤与 Retry budget 恢复，但 `_resume_version()` 与 `_complete_if_all_nodes_resumed()` 仅作为辅助方法存在，未在 Runtime 主入口形成实际 continuation 闭环。

此前已发现 Durable Frontier 的 Multi-frontier 路径存在第二个持久化边界：共享 `WorkflowRuntime._execute_multi_frontier()` 在 Branch 全部成功后会提前追加一次 `frontier_completed` Checkpoint，而 `PlannerDrivenDurableFrontierWorkflowWorker` 随后还会调用 `complete_frontier_with_checkpoint()`，再次追加同一 Frontier 的完成快照。虽然两次写入处于同一事务，但会产生重复的 Execution-level completion fact，并削弱 Frontier → Checkpoint → Next Frontier 单一原子边界的语义。

本轮继续收紧该边界：即使未来调用方误把 Node identity、status 或 I/O 传入统一 progression primitive，`frontier_completed` Contract 也必须在任何数据库写入前拒绝，而不能依赖调用方自律。

## 修复边界

- Resume Runtime 主入口先恢复持久化 Retry budget。
- 线性 Workflow 在进入唯一 `WorkflowRuntime` 前应用 `_resume_version()`，过滤当前 Execution 已完成的 Node。
- 所有线性 Node 已完成时直接使用最后一个 durable Node output 完成 Execution，不重新执行 Node。
- DAG Workflow 不复制 Planner；继续由既有 DAG Planner / Executor 处理。
- Durable Frontier Worker 的 Multi-frontier Adapter 继续复用唯一 `WorkflowRuntime` 的 Node Retry / Execution 能力。
- Durable Frontier Adapter 不再调用会提前持久化 `frontier_completed` 的共享 Multi-frontier helper；Branch Node facts 在当前事务中完成，最终 Frontier Checkpoint、Next Frontier 与 Frontier 状态统一交给 `complete_frontier_with_checkpoint()`。
- `frontier_completed` 被正式定义为 Execution-level snapshot：禁止携带 Node identity、Node status、Node input/output。
- Node-level Checkpoint 仍可携带 Node identity、attempt、status 与 I/O；两种 Checkpoint 层级通过 progression Contract 明确隔离。
- Retry budget、Node attempt、Worker fencing generation 继续保持独立语义。

## 关键不变量

```text
completed Node fact
    ↓
Resume Runtime
    ↓
skip completed Node
    ↓
continue unfinished Node
```

```text
Multi-frontier Branch Node facts
    ↓
唯一 Durable Frontier progression
    ↓
frontier_completed Checkpoint
    ↓
Next Frontier
```

```text
frontier_completed
    ├── Execution snapshot
    ├── no node_id
    ├── no node_status
    ├── no input_data
    └── no output_data
```

同一个 Durable Frontier 成功执行只能产生一个 `frontier_completed` completion fact；普通 WorkflowRuntime 的既有 Checkpoint 语义不因 Durable Frontier Adapter 改造而改变。

## 测试范围

本轮只新增/更新 Unit Test，不执行 pytest。不得把未执行结果记录为 PASS。

新增边界测试覆盖：`frontier_completed` 携带 Node fact 时必须在 progression 写入前拒绝；Node-level Checkpoint 仍允许正常携带 Node fact。