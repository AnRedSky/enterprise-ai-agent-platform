# Durable Frontier Execution-aware Claim 边界

日期：2026-08-27

## 问题

Durable Frontier 原先仅依据 Frontier 自身的 `pending/retry_wait` 状态进行 Claim，然后才读取关联 `WorkflowExecution`。如果旧 Frontier 关联的 Execution 已经进入 `completed`、`failed` 或 `cancelled`，Worker 才在后置检查中回滚事务。

该顺序会让不可消费 Frontier 参与调度排序，并可能形成 head-of-line blocking：最早的不可消费 Frontier 反复被选中，后续真正可执行 Frontier 得不到 Claim。

## 修复

将 Execution ownership / status eligibility 前移到 `claim_next_frontier()` 的同一数据库事务中：

```text
Frontier pending/retry_wait
        +
关联 Execution 可被当前 Worker 消费
        ↓
row lock / claim
        ↓
Frontier attempt + 1
```

允许的 Execution 条件：

1. `pending` 且 owner 为空或 Execution lease 已失效；
2. `running` 且 owner 为当前 Worker；
3. `running` 且 Execution lease 已失效，可进入新的 fencing generation 接管。

终态 Execution 不再被 Durable Frontier Claim 选中。

## 不变量

- Frontier Claim 与 Execution eligibility 必须保持 tenant scope。
- Frontier `attempt` 仍只在成功 Claim 时递增。
- Lease recovery 不直接递增 Frontier `attempt`。
- 终态 Execution 不允许产生新的 Worker Runtime 消费。
- 不复制 Runtime、Planner 或 Recovery 算法。

## Unit Test 范围

仅增加静态 Unit Test Contract，验证 Claim repository 使用 Execution join、pending/running eligibility 以及排除终态；本轮不执行完整测试流程。
