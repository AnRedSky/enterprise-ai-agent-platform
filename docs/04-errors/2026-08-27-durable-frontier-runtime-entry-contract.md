# Durable Frontier Runtime Entry Contract

日期：2026-08-27

## 问题

Durable Frontier Worker 已经能够 Claim `pending` Execution，也能够在同一 Execution 内复用 `running + same owner` 的 Worker fencing generation 继续领取后继 Frontier，但原有 `WorkflowExecutionService.run()` 只接受 `pending` Execution。

这会形成：

```text
Next Frontier
  ↓
Execution = running
  ↓
DurableFrontierWorkflowWorker
  ↓
WorkflowWorker.execute_claimed()
  ↓
只有 pending 可以 Run
  ↓
Runtime 无法继续
```

## 根因

Frontier 是 durable work item；WorkflowExecution 才是 Runtime execution identity。后继 Frontier 不应创建新的 Execution，也不应伪造新的 fencing generation，但 Runtime Entry 原先没有区分：

1. `pending + current owner`：新 Execution 首次启动；
2. `running + same owner + same fencing generation`：同一 Execution 的后继 Frontier 继续运行。

## 修复边界

新增 `workflow_worker/runtime_entry.py` 作为 Runtime Entry Contract：

```text
Durable Frontier Claim
        ↓
Execution ownership / fencing
        ↓
Runtime Entry
   ├── pending → service.transition(..., running)
   └── running + same owner → continue
        ↓
WorkflowRuntime
        ↓
WorkflowExecutionService.transition / Checkpoint fencing
```

该入口不复制 Node Runtime 算法；Node 执行仍统一委托 `WorkflowRuntime`，Execution 状态转换仍统一通过 `WorkflowExecutionService.transition()`。

## Lease 不变量

Runtime Entry 必须继续由 `WorkflowWorkerLeaseGuard` 监督。明确失去 Execution ownership 后立即取消 Runtime，不允许旧 Worker 继续 Provider 调用或写入终态。

```text
lease lost
  ↓
WorkflowWorkerLeaseLost
  ↓
Runtime cancelled
  ↓
旧 Worker 不再 transition
  ↓
Recovery / 新 Worker generation 接管
```

## Unit Test 范围

新增验证：

- Durable Frontier 使用统一 Runtime Entry；
- `pending` Execution 执行正式 `pending → running`；
- `running + same owner` 可以继续 Runtime；
- Runtime Entry 继续使用 LeaseGuard / fencing；
- Lease Lost 后不继续修改 Execution。

当前仅实现 Unit Test，未执行完整测试流程，不记录 PASS。
