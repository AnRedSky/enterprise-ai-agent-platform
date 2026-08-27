# Durable Frontier Terminal Execution Recovery Guard

## 1. 问题

Durable Frontier 允许 Worker lease 到期后由 Recovery Scheduler 将 `claimed/running` Frontier 回收到 `retry_wait`。如果关联 `WorkflowExecution` 已经在另一个事务中进入 `completed`、`failed` 或 `cancelled`，旧 Frontier 仍可能被错误重新打开。

这会产生：

```text
Execution terminalized
        ↓
old Frontier lease expires
        ↓
Recovery Scheduler
        ↓
Frontier → retry_wait
        ↓
Claim
        ↓
terminal Execution 被旧 Frontier 重新消费
```

这违反 Durable Execution 的 terminalization 不可逆原则。

## 2. 修复

`recover_expired_frontiers()` 现在必须 Join `WorkflowExecution`，并要求关联 Execution 状态属于：

```text
pending
running
```

只有这两种状态允许过期 Frontier 进入 `retry_wait`。

```text
claimed/running Frontier
        ↓
lease expired
        ↓
Execution status
   ┌────┴────┐
pending/running  terminal
   ↓               ↓
retry_wait         ignore
   ↓
Worker Claim
```

Recovery 仍然只清理 Frontier ownership，不递增 Frontier attempt；Execution terminalization 不会被 Recovery 回滚或重新打开。

## 3. Contract

必须满足：

1. `completed / failed / cancelled` Execution 不得重新产生可消费 Frontier。
2. stale Worker lease 到期只能恢复仍属于可恢复 Execution 的 Frontier。
3. Recovery 不得改变 terminal Execution 状态。
4. Frontier Recovery 与 Execution 状态判断必须处于同一数据库事务 / 行锁语义内。
5. Tenant boundary 必须同时匹配 `WorkflowFrontier.tenant_id` 与 `WorkflowExecution.tenant_id`。

## 4. Unit Test

新增：

`backend/tests/unit/test_frontier_recovery_contract.py`

覆盖：

- Recovery 查询包含 Execution terminal-status guard。
- 过期 Frontier 回收后清除 Worker ownership。
- Frontier 转入 `retry_wait` 并设置 `FRONTIER_LEASE_EXPIRED`。
- `limit <= 0` 参数拒绝。

按照当前开发策略，本轮只实现 Unit Test，未执行 pytest，不记录 PASS。

## 5. 后续主线

继续验证：

```text
Frontier completion
  ↓
Next Frontier deterministic identity
  ↓
Execution terminalization
  ↓
Expired Frontier Recovery
  ↓
Worker Claim / Fencing
  ↓
Recovery / Replay
```

重点继续收口重复消费、terminalization、stale Worker late-write 与 deterministic Next Frontier identity 的交叉窗口。
