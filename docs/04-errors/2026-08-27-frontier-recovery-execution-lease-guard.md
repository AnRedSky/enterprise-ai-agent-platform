# 2026-08-27 Durable Frontier Recovery Execution Lease Guard

## 1. 问题

`recover_expired_frontiers()` 原先只判断 Frontier 自身的 lease 是否过期，同时要求关联 Execution 为 `pending/running`。这不足以证明旧 Worker 已经失去整个 Execution ownership。

可能出现：

```text
Worker A
  ├── Execution lease：仍有效
  └── Frontier lease：已过期

Recovery Scheduler
  ↓
Frontier → retry_wait
  ↓
Worker B
  ↓
重新 Claim Frontier
```

此时 Worker A 仍可能继续持有并执行同一个 Execution，Worker B 又获得同一个 Frontier，形成双重消费窗口。

## 2. 根因

Frontier lease 与 Execution lease 是同一个 Worker epoch 的两层持久化事实。仅验证 Frontier lease 过期会把局部调度权失效误认为整个 Execution ownership 已失效。

## 3. 修复

`backend/app/services/workflow/frontier_repository.py` 新增统一 `_execution_recoverable_filter(now)`，Recovery 必须同时满足：

```text
Execution status ∈ {pending, running}
        AND
Execution owner is NULL
     OR Execution lease is NULL
     OR Execution lease <= now
```

因此：

```text
Frontier lease expired
+ Execution lease active
        ↓
不 Recovery
```

只有 Execution ownership 同时失效时，Frontier 才能进入 `retry_wait`。

## 4. 设计边界

- 不递增 Frontier `attempt`；
- 不直接修改 Execution 状态；
- 不创建新的 Worker ownership；
- Recovery 仍由调用方事务提交；
- completed / failed / cancelled Execution 继续不能被 Recovery 重新激活；
- Claim、Runtime、Fencing 仍由既有正式入口负责。

## 5. 单元测试

新增：

```text
backend/tests/unit/test_frontier_recovery_lease_guard.py
```

验证 Recovery SQL 条件同时包含：

- Execution owner 为空；
- Execution lease 为空；
- Execution lease 已过期。

本轮未执行 pytest，不能记录 PASS。

## 6. 后续主线

继续检查 Recovery re-entry 与 Concurrent Worker Claim 的完整生命周期，最终保证：

```text
旧 Worker lease 失效
        ↓
Execution ownership 失效
        ↓
Frontier Recovery
        ↓
唯一 Next/Current Frontier Claim
        ↓
新的 Worker epoch
        ↓
Runtime
        ↓
Completion / Replay convergence
```
