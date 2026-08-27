# 2026-08-27 — Durable Frontier Checkpoint Writer / Replay Symmetry

## 审计发现

在上一轮将 Replay 与 `worker_owner` 解耦后，继续审计发现 `WorkflowExecutionCheckpointService.append_next_in_transaction()` 的 writer-side 幂等判断仍使用 `worker_owner`，并且只读取最新一条 `frontier_completed` Checkpoint。

因此仅修改 progression Replay reader 并不足够：新 Worker 直接进入 Checkpoint writer 时仍可能因 owner 变化追加第二条事实；历史已经存在多个 completion facts 时 writer 也可能只取一条而掩盖分叉。

## 修复

`frontier_completed` writer 现在：

1. 不再将 `worker_owner` 作为 Durable completion identity；
2. 查询同一 `execution_id + frontier_id + checkpoint_reason` 的全部 completion facts；
3. `0` 条：允许创建；
4. `1` 条且 lifecycle + payload 相同：返回既有 fact；
5. `>1` 条：立即 `409` fail-closed，不再追加新 fact；
6. 当前 Worker owner / attempt / lease 仍由独立 fencing 参数负责 stale Worker 防护。

## 不变量

```text
Original completion
    ↓
(frontier_id, reason, execution, lifecycle, payload)
    ↓
Replay / duplicate writer
    ↓
同一 Durable identity
    ↓
返回既有 fact
```

```text
multiple completion facts
    ↓
FAIL CLOSED
```

## Unit Test

新增：

```text
backend/tests/unit/test_checkpoint_duplicate_completion_guard.py
```

并保留：

```text
backend/tests/unit/test_checkpoint_replay_worker_independence.py
```

## 测试状态

按照当前开发阶段要求，本轮没有执行 pytest、Regression、E2E 或本地手动测试。
