# 2026-08-27 — Durable Frontier Checkpoint Replay Owner Independence

## 问题

Phase 2.7 Replay convergence 审计发现：`WorkflowExecutionCheckpointService.append_next_in_transaction()` 的 `frontier_completed` 幂等判断同时比较了历史 Checkpoint 的 `worker_owner` 与本次调用的 `worker_owner`。

这与 Replay 的生命周期边界冲突：`worker_owner` 属于 transient ownership / fencing metadata。Worker lease 失效后由新 Worker 恢复并 Replay 同一 Durable completion fact 是合法路径，不应因为 Worker owner 变化而追加第二条 completion Checkpoint。

## 风险

旧逻辑可能形成：

```text
原始 completion
  worker_owner = worker-old
       ↓
已有 frontier_completed Checkpoint
       ↓
新 Worker Replay
  worker_owner = worker-new
       ↓
幂等判断失败
       ↓
追加第二条 completion Checkpoint
```

这会破坏同一 source Frontier + completion reason 的 Durable fact 唯一性。

## 修复

`frontier_completed` 的幂等 identity 不再包含 `worker_owner`。

当前 Durable identity 保留：

```text
source Frontier
+ checkpoint reason
+ execution
+ execution lifecycle
+ checkpoint payload
```

Worker owner / attempt / lease 仍由当前写入路径用于 stale Worker fencing，但不参与历史 Replay fact 的身份判断。

## Unit Test

新增：

```text
backend/tests/unit/test_checkpoint_replay_worker_independence.py
```

覆盖：

```text
existing Checkpoint worker_owner = worker-old
Replay worker_owner            = worker-new
        ↓
返回 existing Checkpoint
不执行 db.add()
不执行 db.flush()
```

## 当前测试状态

本轮按照开发计划没有执行 pytest、Regression、E2E 或本地手动测试。

禁止将该 Unit Test 的实现视为测试 PASS。

## 结论

Replay identity 必须由 Durable facts 证明，不能由当前 Worker ownership 证明。
