# Durable Frontier Execution Worker Epoch Binding

- 日期：2026-08-27
- 范围：Phase 2.7 Durable Frontier / Recovery / Replay Closure
- 状态：已修复

## 问题

此前 `complete_frontier_with_checkpoint()` 在继续 Frontier 时把 `Frontier.attempt` 直接作为 Checkpoint Worker fencing generation 传入。该字段语义不一致：

- `WorkflowExecution.worker_attempt`：Execution 级 Worker ownership epoch，用于判断 Recovery 后当前 Worker 是否仍是同一个 durable owner。
- `WorkflowFrontier.attempt`：单个 Frontier 的 consumption attempt，用于 Frontier 自身的重复消费 fencing。

一个 Execution 可以合法拥有多个 Frontier，因此多个 Frontier 可以共享同一个 Execution Worker epoch，而各自拥有独立的 Frontier attempt。

## 风险

如果把 Frontier attempt 当成 Execution worker epoch，可能导致：

```text
Execution epoch = 7
Frontier F1 attempt = 1
Frontier F2 attempt = 1
        ↓
F1 completion
        ↓
Checkpoint fencing 使用 1
        ↓
错误地把 Frontier consumption attempt 当成 Worker ownership epoch
```

Recovery 后尤其危险，因为旧 Worker 与新 Worker 的真正 fencing 边界在 Execution ownership epoch，而不是某一个 Frontier 的 attempt。

## 修复

`complete_frontier_with_checkpoint()` 现在在 Durable progression 前锁定关联 `WorkflowExecution`，并验证：

```text
execution.worker_owner == worker_owner
AND
execution.worker_lease_expires_at > now
```

随后捕获：

```text
execution_worker_attempt = execution.worker_attempt
```

继续存在 Next Frontier 时，`append_next_in_transaction()` 使用该 Execution epoch：

```text
expected_worker_owner = worker_owner
expected_worker_attempt = execution_worker_attempt
```

而 Frontier transition 仍然独立使用：

```text
worker_owner
frontier.attempt
frontier.worker_lease_expires_at
```

因此两种 fencing 语义保持正交。

## 事务边界

Execution 在同一事务中被 `FOR UPDATE` 锁定。终态 completion 在清除 Execution owner / lease 后追加 Execution-level completion Checkpoint，因此该终态 Checkpoint 不再次通过已经清除的 owner 做二次 fencing；其前置 owner / lease 验证已经在同一事务内完成。非终态 Next Frontier Checkpoint 则在 Execution owner 尚未清除时继续执行显式 epoch 校验。

## 结果

```text
Worker Epoch
    ↓
Execution ownership
    ↓
Checkpoint fencing

Frontier Attempt
    ↓
Frontier ownership
    ↓
Frontier transition fencing
```

二者不再互相替代，为 Recovery、Concurrent Claim、Replay convergence 提供明确的分层 fencing contract。

## 测试

新增 Unit Test：

```text
backend/tests/unit/test_frontier_progression_worker_epoch.py
```

本轮未执行 pytest；测试只实现 Contract，不声明 PASS。