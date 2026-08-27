# Durable Frontier Failure Terminalization Sibling Closure

## 发现

Failure terminalization 原本能够在同一补偿事务内将当前 Frontier 收敛为 `failed` 并将 WorkflowExecution 标记为 `failed`，但同一 Execution 仍可能存在其他 `pending` / `retry_wait` / `claimed` / `running` sibling Frontier。

如果这些 sibling Frontier 保留原状态，会形成“Execution 已 failed，但 Durable work item 仍可被恢复/调度”的生命周期漂移。虽然 Claim eligibility 已排除 failed Execution，但这些 Frontier 本身会成为遗留的不可消费 Durable facts，并可能干扰后续恢复、审计和 Replay 收敛。

## 修复

`PlannerDrivenDurableFrontierWorkflowWorker._mark_execution_failed_in_transaction()` 现在在 Execution 进入 `failed` 的同一数据库事务内调用 `_mark_active_sibling_frontiers_failed()`。

该操作将同一 Execution 下仍处于：

- `pending`
- `retry_wait`
- `claimed`
- `running`

的 sibling Frontier 统一置为 `failed`，同时清除：

- `worker_owner`
- `worker_lease_expires_at`

并写入统一的 `error_code` / `error_message` / `completed_at`。

## 并发边界

该 sibling closure 不再通过逐条 `FOR UPDATE` 获取 sibling Frontier 锁，避免与 Worker Runtime 已持有 Frontier 锁后等待 Execution 锁的路径形成反向锁序。

Execution 行已经由 failure convergence 事务锁定；sibling closure 使用单条 `UPDATE`，数据库自身负责等待正在修改 sibling Frontier 的事务完成。任何旧 Worker 后续进入 terminalization 时仍必须重新取得 Frontier → Execution ownership / lease fencing，因此不能覆盖已经 failed 的 Execution。

## Durable 不变量

```text
Execution = failed
        ↓
同 Execution 不得存在
pending / retry_wait / claimed / running Frontier
        ↓
所有 sibling Frontier = failed
        ↓
所有 sibling Worker ownership / lease = NULL
```

这使 Failure terminalization 与 Success terminalization 一样具备完整的 Execution-level lifecycle closure。

## Unit Test

新增 `backend/tests/unit/test_frontier_failure_terminalization.py`，覆盖：

1. Failure terminalization 调用 sibling Frontier closure；
2. 已 failed Execution 的重复 failure 仍保持 sibling closure。

## 测试状态

本轮仅实现 Unit Test，**未执行 pytest、集成测试、Real API、E2E 或本地手动测试**。不得将未执行测试标记为 PASS。
