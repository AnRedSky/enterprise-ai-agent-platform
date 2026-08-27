# 工程错误记录：Durable Frontier stale Worker lease completion

- 日期：2026-08-27
- Phase：Phase 2.7-A Durable Recovery Closure
- 类型：并发控制 / Worker fencing / Durable Frontier
- 状态：已修复

## 问题

`transition_owned_frontier()` 原先只验证 Frontier 的 `worker_owner` 与 `attempt`。当 Worker lease 已经过期、但 Recovery 尚未完成并发清理时，旧 Worker 仍可能使用原 owner 与 attempt 通过最终状态推进条件。

```text
Worker A
  ↓
Frontier owner=A / attempt=N
  ↓
lease 已过期
  ↓
Recovery 尚未完成清理
  ↓
Worker A completion/failure
  ↓
仅 owner + attempt 校验可能通过
```

这会形成 stale Worker 在 lease 生命周期之外继续写入 `completed/failed` durable state 的窗口。

## 根因

Frontier ownership 的有效性由三个维度共同定义：

```text
worker_owner
+
attempt
+
worker_lease_expires_at > now
```

只校验前两个维度无法证明当前 Worker 仍处于有效 execution epoch。

## 修复

`backend/app/services/workflow/frontier_repository.py` 的 `transition_owned_frontier()` 现在在同一个 `SELECT ... FOR UPDATE` 条件中同时要求：

- `worker_owner == worker_owner`
- `attempt == attempt`
- `worker_lease_expires_at IS NOT NULL`
- `worker_lease_expires_at > now`
- Frontier 当前状态仍为 `claimed/running`

因此 stale Worker 会在最终 Durable transition 入口被拒绝。

Recovery 仍然通过行锁与状态/ownership 清理形成竞争收敛；新的 Worker 只能在有效 Claim 后获得新的 Frontier attempt。

## 不变量

```text
lease expired
    ↓
旧 Worker 不得 completion / failure

owner + attempt + unexpired lease
    ↓
才允许 Frontier terminal transition
```

该规则不会替代已有的 Execution ownership / fencing，也不会取消数据库行锁；它是 Frontier 最终写入口的最后一道 lease validity guard。

## Unit Test

新增 `backend/tests/unit/test_frontier_stale_lease_completion.py`，覆盖：

- terminal transition 必须校验未过期 lease；
- stale Worker 错误语义必须明确包含 lease/fencing 失效；
- attempt fencing 与 `FOR UPDATE` 不得被移除。

本轮按开发策略只实现 Unit Test，未执行 pytest。
