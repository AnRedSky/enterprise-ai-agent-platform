# Durable Frontier Planner Runtime Lease-Lost Abort

## 日期

2026-08-27

## 问题

Durable Frontier 基础 Worker 已经能够在 Frontier / Execution lease 失效时取消正在运行的 Runtime，但 `PlannerDrivenDurableFrontierWorkflowWorker` 重写 `execute_frontier()` 后，如果 heartbeat 只结束自身而没有取消 Planner/DAG Runtime，旧 Worker 仍可能继续执行 Node，并在后续 durable boundary 才被拒绝。

这会扩大 stale Worker 的执行窗口，并让 Recovery 与旧 Runtime 并发。

## 修复

Planner-driven Frontier Runtime 启动 heartbeat 时显式传递当前 `execute_frontier()` task：

```text
execute_frontier()
    ↓
runtime_task = current_task()
    ↓
heartbeat(frontier, attempt, runtime_task)
```

当原子 Frontier + Execution lease heartbeat 发现 ownership 失效时：

```text
lease lost
    ↓
runtime_task.cancel()
    ↓
Planner / DAG Runtime CancelledError
    ↓
事务 rollback
    ↓
不进入普通 `_converge_failure()`
    ↓
Recovery Worker 接管
```

## 关键不变量

- Lease loss 属于 Worker ownership 丢失，不属于普通业务执行失败；
- `CancelledError` 不得被转换成 Frontier retry / failed durable fact；
- 当前 Node / Checkpoint 事务必须 rollback；
- 旧 Worker 不得在 lease loss 后继续产生新的 durable fact；
- Recovery Worker 使用新的 Execution worker epoch 接管后才能继续执行。

## 当前验证状态

本记录对应生产代码变更。按照当前开发策略，本轮不执行 pytest、集成测试或本地手动测试，因此不得将测试标记为 PASS。
