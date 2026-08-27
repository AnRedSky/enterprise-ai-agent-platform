# 2026-08-27 — Frontier Completion Checkpoint 重复持久化

## 问题

当前 Durable Frontier Worker 已经通过 `complete_frontier_with_checkpoint()` 形成：

```text
Frontier completed
    ↓
Execution-level frontier_completed Checkpoint
    ↓
Next Frontier enqueue
```

但 Multi-frontier Runtime 在 Join-ready 后也会直接追加一次 `frontier_completed` Checkpoint。
因此 Runtime 与 Frontier progression 接线时，同一事务可能针对完全相同的 merged state 产生两个 Execution-level Checkpoint sequence。

## 根因

两个层次都认为自己拥有 `frontier_completed` 的最终 durable boundary：

```text
WorkflowRuntime._execute_multi_frontier()
        ↓
frontier_completed

complete_frontier_with_checkpoint()
        ↓
frontier_completed
```

Checkpoint Service 原先只负责追加 sequence，没有针对相同 Execution-level completion fact 的幂等收敛。

## 修复

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 在已经锁定 Execution、完成 tenant / Worker fencing 校验后，对 `frontier_completed` 查询最新同原因 boundary：

```text
same execution
AND checkpoint_reason = frontier_completed
AND execution_status 相同
AND state_data 相同
AND worker_owner 相同
        ↓
复用已有 Checkpoint
        ↓
不创建新 sequence
```

如果 merged state 不同，则继续创建新的 Checkpoint，不掩盖真实状态推进。

## 不变量

1. Checkpoint 仍然是 append-only durable fact；普通不同事实不会被覆盖。
2. 幂等复用只针对完全相同的 Execution-level `frontier_completed` durable boundary。
3. Execution 行锁、tenant scope 与 Worker fencing 仍然是复用前置条件。
4. 不新增 Runtime / Planner / Frontier Repository。
5. `complete_frontier_with_checkpoint()` 的 Frontier → Checkpoint → Next Frontier 事务边界保持不变。

## Unit Test

新增：

- `test_frontier_completed_checkpoint_reuses_same_boundary`
- `test_frontier_completed_checkpoint_does_not_reuse_different_state`

当前环境没有执行 pytest，因此不能记录 PASS。
