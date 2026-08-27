# Phase 2.6 Lease Loss Active Abort

## 状态

**实现完成，进入 Phase 2.6 Closure Review。**

## 本轮目标

在 Worker 已具备 expired running reclaim、lease 与 ownership fencing 后，补齐最后一个运行时安全窗口：旧 Worker 在 heartbeat 明确失去 ownership 后，必须主动取消正在执行的 WorkflowRuntime，而不是继续执行到下一次状态转换才因 fencing 失败。

## 实现

- `backend/app/services/workflow_worker/lease_guard.py` 提供 `WorkflowWorkerLeaseGuard`；
- `backend/app/services/workflow_worker/lease_runtime.py` 将 Guard 正式接入公开 `WorkflowWorker` Runtime；
- 默认 Worker 入口现在使用 `LeaseAwareWorkflowWorker`；
- Guard 的 `renew_lease()` 使用现有 Worker 原子 ownership fencing，不复制 PostgreSQL lease 状态机；
- `renew_lease()` 返回 `False` 时转换为 `WorkflowWorkerLeaseLost` 并立即取消底层 Runtime task；
- lease heartbeat 瞬时异常不会直接判定 ownership 丢失，而是继续下一轮 heartbeat；
- stale Worker 被取消后不再主动推进 Execution；新 Worker 可以通过 expired running reclaim 接管；
- Recovery Worker telemetry 在主动中止场景记录 `outcome=aborted`、`reason_code=WORKER_LEASE_LOST`，避免把被取消的旧 Worker 错误记录成 completed；
- 原有 claim、lease refresh、fencing、timeout、Recovery Trace 与 WorkflowRuntime 状态机继续复用，没有建立第二套 Worker Runtime。

## 生命周期

```text
Worker claim
    ↓
Runtime executing
    ↓
lease heartbeat
    ├── owned = True → Runtime continues
    ├── transient error → retry heartbeat
    └── owned = False
             ↓
       WorkflowWorkerLeaseLost
             ↓
       cancel Runtime task
             ↓
       stale Worker exits
             ↓
       new Worker reclaim / resume
```

## Telemetry Contract

```text
Recovery Trace R
      ↓
Worker started
      ↓
Runtime executing
      ↓
lease ownership lost
      ↓
Worker Runtime aborted
      ↓
Worker finished
outcome = aborted
reason_code = WORKER_LEASE_LOST
```

Trace 不携带 Checkpoint `state_data`、Prompt、Secret、Provider credential 或完整业务 payload。

## Unit Test

新增/保留覆盖：

1. lease 明确失效时 Runtime 被主动取消；
2. Runtime 正常完成优先于 lease monitor；
3. 单次 heartbeat 异常不会误触发 Runtime 中止；
4. 默认公开 `WorkflowWorker` 使用 `LeaseAwareWorkflowWorker`；
5. 默认 Worker Runtime 的底层执行任务在 lease loss 后确实收到 cancellation。

本轮仅保留 Unit Test；未实际执行的测试不得记录为 PASS。

## Closure Review

下一阶段不再增加平行 Lease / Trace 抽象，只做 Phase 2.6 Closure：

- Checkpoint / Resume / Recovery Contract 一致性；
- Scheduler → Recovery → Resume Trace lineage；
- Worker Claim / Lease / Reclaim / Fencing；
- Lease Loss Active Abort；
- WorkflowRuntime / DAG / Branch / Join / Checkpoint；
- Unit Test 实际执行结果；
- `PROJECT_STATUS.md` 与 Phase 文档最终状态。
