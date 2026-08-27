# Phase 2.6 Lease Loss Active Abort

## 本轮目标

在 Worker 已具备 expired running reclaim、lease 与 ownership fencing 后，补齐最后一个运行时安全窗口：旧 Worker 在 heartbeat 明确失去 ownership 后，必须主动取消正在执行的 WorkflowRuntime，而不是继续执行到下一次状态转换才因 fencing 失败。

## 实现

新增 `backend/app/services/workflow_worker/lease_guard.py`：

- `WorkflowWorkerLeaseGuard` 负责监督 Runtime 与 lease heartbeat 生命周期；
- `renew_lease()` 返回 `False` 时转换为 `WorkflowWorkerLeaseLost`；
- 明确失去 ownership 后立即取消 Runtime task；
- 单次数据库/heartbeat 异常不等价于 ownership 丢失，继续下一轮 heartbeat；
- 不直接操作 PostgreSQL，不复制 Worker lease 状态机；真实 lease refresh 仍由 Worker 的原子 ownership fencing 实现负责。

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

## Unit Test

新增覆盖：

1. lease 明确失效时 Runtime 被主动取消；
2. Runtime 正常完成优先于 lease monitor；
3. 单次 heartbeat 异常不会误触发 Runtime 中止。

本轮仅新增可执行 Unit Test，未将未实际执行的测试记录为 PASS。

## 下一收口

完成 Worker Lease Loss Active Abort 的正式 Runtime 集成后，进入 Phase 2.6 Closure Review：统一检查 Checkpoint、Recovery、Trace、Lease、Fencing、Worker、Runtime、Join 和文档状态，不再继续增加平行 Durable Execution 抽象。
