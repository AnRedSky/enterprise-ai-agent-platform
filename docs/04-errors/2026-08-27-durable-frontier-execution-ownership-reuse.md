# 2026-08-27 — Durable Frontier 继续执行时的 Execution ownership 复用

## 问题

当前默认 Worker 已经以 `PlannerDrivenDurableFrontierWorkflowWorker` 作为 Durable Frontier 调度入口，但 `claim_one_frontier()` 原先只接受 `pending` Execution。

因此一个 Execution 完成首个 Frontier 后仍保持 `running + worker_owner`，虽然下一 Frontier 已经通过统一 progression Contract 持久化进入 `pending`，Worker 却无法继续领取它，形成：

```text
Frontier A
  ↓
Execution running + owner=A
  ↓
Frontier B pending
  ↓
Worker claim Frontier B
  ↓
只能接受 pending Execution
  ↓
错误回滚
  ↓
Frontier B 无法继续执行
```

## 修复

`DurableFrontierWorkflowWorker.claim_one_frontier()` 现在区分三种 Execution ownership 情况：

1. `pending` 且无 owner / lease 已过期：取得当前 Worker ownership，并递增 Execution fencing generation。
2. `running` 且 owner 已经是当前 Worker：继续复用当前 fencing generation，只刷新 Execution lease，不递增 `worker_attempt`。
3. `running` 且原 owner lease 已过期：接管 Execution，重新取得 ownership 并递增 fencing generation。

其他有效 Worker 持有的 `running` Execution 不允许被抢占。

## 关键不变量

- 同一 Worker 在同一 Execution 内继续消费后继 Frontier，不产生虚假 fencing generation。
- Worker 接管过期 Execution 时必须产生新的 fencing generation，使旧 Worker 的后续状态写入失效。
- Frontier claim 与 Execution ownership 仍在同一数据库事务内完成。
- 不新增 Runtime、Planner、Checkpoint 或 Retry 实现。

## Unit Test

新增静态 Contract 检查：

- 默认 Worker 使用 `PlannerDrivenDurableFrontierWorkflowWorker`；
- 当前 Worker 复用 `running` Execution 时不改变 generation；
- 外部 Worker lease 过期后必须进入新的 fencing generation。

当前环境未执行 pytest，因此不记录 PASS。
