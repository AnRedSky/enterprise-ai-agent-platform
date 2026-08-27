# 2026-08-27 Node Checkpoint Stale Worker Fencing

## 问题

Execution 与 Checkpoint 已分别具备 Worker owner/generation fencing，但 `WorkflowExecutionService.transition_node()` 在 Node 完成后调用 Checkpoint Durable 写入时，如果只传递 `worker_owner`，无法保证同一 Worker 在 generation 变化后不能继续追加 Checkpoint。

## 根因

Worker context 的 fencing identity 是：

```text
worker_owner + worker_attempt
```

`WorkflowExecutionService._lock_execution()` 会在 Node 状态转换前重新锁定 Execution 并校验该 generation；但 Node 完成后的 Checkpoint append 必须继续携带同一个 generation，才能让 Checkpoint Service 在自己的 `FOR UPDATE` 边界再次校验。

## 修复

`transition_node()` 的 `node.completed` Checkpoint 写入现在显式传递：

```text
expected_worker_owner=execution.worker_owner
expected_worker_attempt=execution.worker_attempt
```

Checkpoint Service 锁定目标 Execution 后执行：

```text
locked owner == expected owner
AND
locked attempt == expected attempt
```

任一不一致均拒绝 Durable Checkpoint 写入。

## 结果

形成完整 stale Worker 防护链：

```text
Frontier fencing
    ↓
Execution fencing
    ↓
Node transition fencing
    ↓
Checkpoint fencing
    ↓
Next Frontier progression
```

同一 Worker 在 lease/reclaim 后 generation 变化，即使旧 Runtime 已经产生 Node completed 结果，也不能通过 Node → Checkpoint 边界产生新的不可变 Durable Fact。

## 验证

新增 Unit Test 对 Worker generation 从 Node transition 到 Checkpoint append 的参数传播进行静态回归保护。

当前开发阶段按治理要求暂停 Full Regression / E2E；本环境无法直接执行 pytest，因此不将未执行结果标记为通过。
