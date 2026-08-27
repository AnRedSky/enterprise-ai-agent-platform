# 2026-08-27 Phase 2.7 Conditional Decision Rebuild

## 问题

Recovery Planner 已经能够从 durable completed Node facts 重新计算 decision fingerprint，但 Replay Guard 过去主要比较 fingerprint。对于已经持久化的 `workflow.dag.frontier_decided`，如果 frontier 或 selected predecessor metadata 与本次重建结果不一致，缺少直接的可观测失败原因。

## 根因

Conditional Decision 的恢复语义必须同时保证：

- completed Node facts 一致；
- decision fingerprint 一致；
- frontier 一致；
- selected predecessor 一致。

Fingerprint 是最终 identity，但 frontier / predecessor 是必须保持可审计一致的 Decision outputs。

## 修复

`WorkflowRecoveryTraceLinkService.assert_dag_decision_replay_consistent()` 现在支持同时校验：

```text
completed_node_ids
+ decision_fingerprint
+ frontier_node_ids
+ selected_predecessors
```

Runtime 在 Recovery trace 存在时，将 Planner 的完整 Decision outputs 交给 Guard。

不一致时立即抛出 `ValueError`，由 DAG Runtime 转换为 HTTP 409，禁止继续使用不一致的 Recovery Decision。

## 不变量

```text
Durable Snapshot
      ↓
Condition Input
      ↓
DAG Planner
      ↓
Fingerprint + Frontier + Predecessors
      ↓
Replay Guard
      ↓
与历史 Decision 完全一致才允许继续
```

Trace 仍然不是业务状态 Source of Truth；业务状态继续来自 PostgreSQL Durable Node / Checkpoint facts。

## 测试范围

新增 Unit Test：

- 相同 fingerprint / frontier / predecessor → 通过；
- fingerprint 改变 → 失败；
- frontier 改变 → 失败；
- selected predecessor 改变 → 失败。

按当前开发策略不执行完整 Regression / E2E / Real API acceptance。
