# 2026-08-27 Multi-frontier Checkpoint Boundary

## 问题

DAG Runtime 已经通过 `WorkflowDagMultiFrontierExecutor` 要求所有 Branch 执行成功并完成 Branch Checkpoint 后才能进入 Join-ready，但 Runtime 原有 `checkpoint_branch()` 仅执行输入校验，没有在整个 frontier 成功收敛后追加 Execution-level `frontier_completed` Checkpoint。

这会造成：

```text
Branch A completed + checkpoint
Branch B completed + checkpoint
        ↓
Join ready
        ↓
缺少 frontier_completed Execution-level durable boundary
```

因此下一次 Resume / Recovery 只能看到最后一个 Node-level Checkpoint，无法把“整个 Multi-frontier 已全部完成并形成 merged state”作为独立 Durable Fact。

## 根因

`WorkflowExecutionService.transition_node(..., completed)` 已经负责 NodeExecution + `node.completed` Checkpoint 的同事务持久化；Multi-frontier Executor 负责 Branch 执行、Branch Checkpoint callback 与 Join readiness，但 Runtime 没有在 `join_ready=True` 后调用统一 Checkpoint Service 写入 Execution-level boundary。

## 修复

`WorkflowRuntime._execute_multi_frontier()` 现在在 `WorkflowDagMultiFrontierExecutor.execute()` 返回 `join_ready=True` 后：

1. 使用已有 `WorkflowExecutionCheckpointService.append_next_in_transaction()`；
2. 写入 `checkpoint_reason="frontier_completed"`；
3. `node_id / node_attempt / node_status` 保持为空，严格遵守 Execution-level boundary；
4. 使用当前 Worker owner + fencing generation；
5. 带当前 tenant scope；
6. 使用 Executor 计算出的 merged state 作为 durable state snapshot；
7. 继续留在当前 Runtime / Worker 事务中，不提前 commit。

## 不变量

```text
all Branch execution success
        AND
all Branch Node Checkpoint success
        ↓
Join ready
        ↓
frontier_completed Checkpoint
        ↓
next frontier planning
```

`join_ready=False` 时绝不写入 `frontier_completed`。

## 测试范围

新增 Unit Test 验证：

- Join-ready 时写入 Execution-level `frontier_completed`；
- 正确传播 tenant / worker owner / fencing generation；
- Join 未就绪时不写 Checkpoint。

本轮不执行 Full Regression、Real API、Browser E2E 或完整 Acceptance。
