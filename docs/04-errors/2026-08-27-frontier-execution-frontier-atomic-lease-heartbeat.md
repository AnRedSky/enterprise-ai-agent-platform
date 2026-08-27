# 2026-08-27 Frontier / Execution Atomic Lease Heartbeat

## 问题

Durable Frontier Worker 之前只通过 `renew_owned_frontier_lease()` 刷新 Frontier lease，而 Planner-driven Frontier Runtime 同时依赖 `WorkflowExecution.worker_owner`、`worker_attempt` 与 `worker_lease_expires_at` 作为 Execution-level Worker fencing。

如果只刷新 Frontier：

```text
Frontier lease = valid
Execution lease = expired
```

就会形成跨层 ownership 不一致窗口。Node / Checkpoint 写入虽然会在 durable boundary 再次检查 Execution lease，但 Runtime 本身可能继续运行，Recovery 也可能在不同时间观察到两层不同的 ownership 状态。

## 根因

Worker runtime 的 Frontier heartbeat 与 Execution heartbeat 没有共享同一个原子续租事务。

Frontier 与 Execution 属于同一次 Worker execution contract，不能允许其中一层续租成功而另一层续租失败后仍提交。

## 修复

`backend/app/services/workflow/frontier_lease_repository.py` 的 `renew_owned_frontier_lease()` 现在：

1. 使用 `worker_owner + frontier attempt + active frontier lease + active frontier status` 原子刷新 Frontier；
2. 获取同一 Frontier 的 `execution_id`；
3. 使用相同 `worker_owner + active Execution status + active Execution lease` 刷新 Execution lease；
4. 任一层失败立即 rollback；
5. 两层全部成功后才由调用方 commit。

因此 heartbeat contract 变为：

```text
Frontier owner / attempt / lease
            +
Execution owner / worker epoch / lease
            ↓
      atomic short transaction
            ↓
       both renewed
```

## 设计边界

- `WorkflowExecution.worker_attempt` 仍然是 Worker ownership epoch；
- `WorkflowFrontier.attempt` 仍然是 Frontier consumption attempt；
- 两个计数器不合并；
- 本修复只解决 lease heartbeat 的原子一致性，不替代最终 durable write boundary 的 fencing；
- Checkpoint / Frontier terminal transition 仍必须独立验证 owner、epoch/attempt 与 active lease。

## 验收要求

Unit Test 应覆盖：

- Frontier 与 Execution 都有效时两者同时续租；
- Frontier ownership 失效时两层都不提交；
- Execution ownership / lease 失效时 Frontier 续租结果 rollback；
- Execution 已进入 terminal 状态时 heartbeat 不得续租；
- 两层续租共享同一个事务边界。

本轮未执行 pytest；不记录测试通过结果。
