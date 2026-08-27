# Durable Frontier Terminalization：Active Sibling Frontier Guard

## 背景

Phase 2.7 的 Success terminalization 在 `next_identity is None` 时会把当前 Frontier、Checkpoint 与 Workflow Execution 收敛到 completed。

## 风险

同一 Execution 允许多个并行 Frontier。若某个 Frontier 在仍存在 `pending` / `retry_wait` / `claimed` / `running` sibling Frontier 时直接 terminalize Execution，会导致：

- sibling Frontier 失去可执行的 Execution lifecycle；
- Recovery / Claim 与 terminalization 观察到矛盾的 Durable facts；
- Replay 无法唯一解释 Execution 为什么已经 completed。

## 本轮实现

在 `complete_frontier_with_checkpoint()` 的 terminal path 中，在已锁定 Execution 后检查同一 Execution 的其他活动 Frontier。

只有不存在活动 sibling Frontier 时，才允许：

```text
Frontier completed
    ↓
Execution completed
    ↓
frontier_completed Checkpoint
    ↓
COMMIT
```

存在 sibling 时直接抛出 `FrontierProgressionContractError`，由外层事务 rollback，不产生新的 terminal Durable fact。

## 并发边界

Execution 行锁先于 sibling 状态检查，Claim / terminalization 继续遵循既定 `Frontier → Execution` 锁序；检查不再额外锁 sibling Frontier，避免引入反向锁等待。

## 测试

新增 Unit Test：

- active sibling 存在时拒绝 terminalization；
- 无 active sibling 时允许继续。

本轮未执行 pytest、集成测试、Real API、E2E 或本地手动测试；不得记录 PASS。
