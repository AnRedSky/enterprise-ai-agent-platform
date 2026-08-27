# 2026-08-27 Durable Frontier 成功持久化路径收敛

## 问题

Durable Frontier Worker 已经能够执行 Planner frontier，但如果 Worker 分别调用 Frontier terminal transition、Checkpoint append 和 Next Frontier enqueue，就会存在多个持久化入口。虽然这些调用可以处于同一事务，但职责容易重新分散，后续修改可能产生部分提交或错误的锁顺序。

## 收敛方案

默认 `PlannerDrivenDurableFrontierWorkflowWorker` 统一调用 `complete_frontier_with_checkpoint()`：

```text
Runtime Node facts
      ↓
complete_frontier_with_checkpoint()
      ├── current Frontier fencing transition
      ├── Checkpoint append / sequence allocation
      ├── Next Frontier deterministic enqueue
      └── outer caller commit
```

Worker 不再分别执行成功路径的 Frontier transition 与 Next Frontier enqueue。

## Node Fact Binding

单 Node Frontier 完成后，从同一事务读取最新 `WorkflowNodeExecution` 的 attempt、status、output，并将其作为 Node-level Checkpoint 的 fact metadata。Multi-frontier 使用 merged state 生成 Execution-level Checkpoint，避免将多个 Branch 错误绑定成一个 Node fact。

## 一致性保证

- 当前 Frontier 必须通过 `worker_owner + attempt` fencing；
- Checkpoint 与 Frontier terminal transition 属于同一个外层事务；
- Next Frontier 使用 deterministic identity 幂等入队；
- 没有 Next Frontier 时最终 Execution 在同一事务内进入 `completed`；
- 任一步失败均由 Worker 回滚整个成功事务，随后进入既有 Retry / Failed compensation path；
- progression primitive 不执行 commit。

## 测试边界

本轮仅补充/保留 Unit Test Contract；当前环境未实际执行 pytest，不记录 PASS。完整回归、E2E、Real API 暂停，不作为当前主线阻塞条件。