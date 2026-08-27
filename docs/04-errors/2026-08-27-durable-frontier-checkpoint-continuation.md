# Durable Frontier Checkpoint Continuation

## 问题

Durable Resume Runtime 已实现 completed Node 过滤与 Retry budget 恢复，但 `_resume_version()` 与 `_complete_if_all_nodes_resumed()` 仅作为辅助方法存在，未在 Runtime 主入口形成实际 continuation 闭环。

本轮继续发现 Durable Frontier 的 Multi-frontier 路径存在第二个持久化边界：共享 `WorkflowRuntime._execute_multi_frontier()` 在 Branch 全部成功后会提前追加一次 `frontier_completed` Checkpoint，而 `PlannerDrivenDurableFrontierWorkflowWorker` 随后还会调用 `complete_frontier_with_checkpoint()`，再次追加同一 Frontier 的完成快照。虽然两次写入处于同一事务，但会产生重复的 Execution-level completion fact，并削弱 Frontier → Checkpoint → Next Frontier 单一原子边界的语义。

## 修复边界

- Resume Runtime 主入口先恢复持久化 Retry budget。
- 线性 Workflow 在进入唯一 `WorkflowRuntime` 前应用 `_resume_version()`，过滤当前 Execution 已完成的 Node。
- 所有线性 Node 已完成时直接使用最后一个 durable Node output 完成 Execution，不重新执行 Node。
- DAG Workflow 不复制 Planner；继续由既有 DAG Planner / Executor 处理。
- Durable Frontier Worker 的 Multi-frontier Adapter 继续复用唯一 `WorkflowRuntime` 的 Node Retry / Execution 能力。
- Durable Frontier Adapter 不再调用会提前持久化 `frontier_completed` 的共享 Multi-frontier helper；Branch Node facts 在当前事务中完成，最终 Frontier Checkpoint、Next Frontier 与 Frontier 状态统一交给 `complete_frontier_with_checkpoint()`。
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

同一个 Durable Frontier 成功执行只能产生一个 `frontier_completed` completion fact；普通 WorkflowRuntime 的既有 Checkpoint 语义不因 Durable Frontier Adapter 改造而改变。

## 测试范围

本轮只新增/更新 Unit Test 实现，不执行 pytest。不得把未执行结果记录为 PASS。
