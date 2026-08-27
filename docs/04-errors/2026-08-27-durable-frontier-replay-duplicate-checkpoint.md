# Durable Frontier Replay Duplicate Completion Fact Closure

## 发现

Replay convergence 原有实现会读取同一 source Frontier 下最新的一条 `frontier_completed` Checkpoint。

这种查询方式能够处理正常的单条 completion fact，但如果数据库中已经存在两条同一 Frontier / completion reason 的 Durable facts，直接 `ORDER BY sequence DESC LIMIT 1` 会把已经发生的 fact 分叉隐藏掉，Replay 可能错误地继续收敛到最新一条事实。

这不符合 Durable Replay 的 fail-closed 原则：一旦同一 source Frontier 已经存在多个 completion facts，应先暴露 Durable consistency violation，而不是猜测哪一条是权威事实。

## 修复

`backend/app/services/workflow/frontier_progression.py` 的 completion Replay binding 现在读取该 source Frontier 的全部匹配 `frontier_completed` Checkpoint：

```text
0 facts
  → Reject: source completion fact missing

1 fact
  → continue strict Replay binding

>1 facts
  → Reject: duplicate Durable completion facts
```

单条 fact 继续执行已有校验：

- Checkpoint payload equality；
- worker owner equality；
- Execution lifecycle equality；
- Next Frontier identity；
- workflow version；
- decision fingerprint；
- Node-set。

## Durable 不变量

```text
one source Frontier
      ↓
one frontier_completed Checkpoint
      ↓
zero / one Next Frontier identity
      ↓
one replay result
```

Replay 不再通过“取最新记录”掩盖已经存在的 duplicate completion facts。

## Unit Test

`backend/tests/unit/test_frontier_duplicate_consumption.py` 新增：

- `test_duplicate_completion_rejects_multiple_completion_checkpoints`

该测试验证同一 Frontier 存在多个 completion Checkpoint 时立即抛出 `FrontierProgressionContractError`，不会继续进入 Execution 或 Next Frontier progression。

## 测试状态

本轮仅实现生产代码与 Unit Test，**未执行 pytest、集成测试、Real API、E2E 或本地手动测试**。不得将未执行测试标记为 PASS。
