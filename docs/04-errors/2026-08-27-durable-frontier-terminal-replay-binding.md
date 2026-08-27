# Durable Frontier 终态 Replay Binding 风险记录

## 发现日期

2026-08-27

## 所属阶段

Phase 2.7 Advanced Workflow Orchestration / Durable Recovery Closure

## 问题

`complete_frontier_with_checkpoint()` 已经能够通过 source Frontier 精确定位 `frontier_completed` Checkpoint，并通过 Frontier identity 防止重复创建相同 Next Frontier。但仅验证 Next Frontier `frontier_key` / Execution / Workflow Version 仍不足以证明重复 completion 与第一次 durable progression 完全一致。

当相同 completion 请求因为 Replay、重复 dispatch 或异常恢复再次进入幂等路径时，理论上可能出现：

```text
第一次 completion
  ├── source Frontier = F
  ├── decision fingerprint = A
  └── Next Frontier = N(nodes=[a,b])

重复 completion
  ├── source Frontier = F
  ├── decision fingerprint = B
  └── Next Frontier identity 使用相同业务上下文但产生 drift
```

仅依赖数据库 `frontier_key` 唯一性不能表达“同一 source Frontier 的 Replay 必须复现同一 decision 与 Node 集合”。

## 处理

在 `_resolve_completed_frontier_idempotency()` 中增加严格绑定：

1. 既有 Next Frontier 必须属于同一 Workflow Execution；
2. 必须属于同一 Workflow Version；
3. `decision_fingerprint` 必须与原始 `next_identity` 完全一致；
4. Node 集合必须与原始 `next_identity.node_ids` 完全一致；
5. 任一 drift 均抛出 `FrontierProgressionContractError`，禁止继续 Replay convergence。

该校验发生在产生新的 durable fact 之前，因此不会通过第二个 Frontier 或第二个 Checkpoint 被动兜底。

## 设计边界

该规则只校验 Replay 的 Durable identity 与 Node-set 一致性，不重新执行 Planner、Condition Evaluator 或 Runtime。Planner 仍是 Decision 的唯一计算来源，Progression 只负责证明重复 durable write 与历史事实一致。

## 测试

新增 Unit Test 覆盖：

- 相同 completion 但 decision fingerprint drift 必须拒绝；
- 相同 fingerprint 但 Next Frontier Node-set drift 必须拒绝。

本轮未执行 pytest、Integration、Real API 或 E2E，因此不得记录 PASS。
