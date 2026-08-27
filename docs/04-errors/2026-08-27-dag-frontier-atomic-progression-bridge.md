# 2026-08-27 — DAG Frontier → Durable Frontier 原子推进接线

## 问题

DAG Next Frontier deterministic identity 已经由 `WorkflowDagFrontierProgressionService` 生成，但此前该模块只返回 identity，没有正式把 Planner 输出接入统一的 `Frontier → Checkpoint → Next Frontier` 持久化 Contract。

如果 Runtime 自己 enqueue Next Frontier，就会产生持久化旁路；如果调用方分别写 Checkpoint 和 Frontier，又可能破坏同事务边界。

## 修复

新增 `WorkflowDagFrontierProgressionService.complete_frontier()`：

```text
current completed durable facts
        ↓
唯一 WorkflowDagResumePlanner
        ↓
WorkflowFrontierIdentity
        ↓
complete_frontier_with_checkpoint()
        ↓
Frontier completed
        ↓
Execution Checkpoint
        ↓
Next Frontier enqueue
```

Planner 只负责计算，统一 Frontier progression contract 负责持久化。该方法本身不 commit，由调用方统一 rollback / commit。

## 不变量

1. 当前 Frontier 未形成完整 completed durable facts 时，不允许进入持久化阶段。
2. Next Frontier identity 必须由唯一 `WorkflowDagResumePlanner` 重新计算。
3. Next Frontier 不允许通过 Runtime 旁路 enqueue。
4. Frontier、Checkpoint、Next Frontier 必须继续使用同一外层事务。
5. Worker ownership / attempt / fencing 继续由既有 `complete_frontier_with_checkpoint()` 处理。
6. Terminal DAG 不产生虚假 Next Frontier，统一由已有 Contract 将 Execution 收敛到 completed。

## Unit Test

新增：

- `test_complete_frontier_delegates_persistence_to_atomic_contract`
- `test_complete_frontier_does_not_persist_when_planning_rejects_incomplete_facts`

当前环境没有执行 pytest，因此不能记录 PASS。
