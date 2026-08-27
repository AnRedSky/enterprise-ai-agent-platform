# 2026-08-27 Durable Frontier 过期租约 Recovery Scheduler 接线

## 问题

Durable Frontier Repository 已具备 `recover_expired_frontiers()`，能够把过期 `claimed` / `running` Frontier 原子回收到 `retry_wait`。但 Scheduler Service 的 Recovery Scan 之前只扫描 `failed WorkflowExecution`，没有周期性调用 Frontier recovery primitive。

因此 Worker 崩溃、进程被终止或 Frontier lease 超时后，Frontier 可能长期停留在过期的 ownership 状态，无法重新进入 Worker Claim 队列。

## 修复

`WorkflowRecoveryScheduler.scan_once()` 现在每轮先调用：

```text
recover_expired_frontiers()
        ↓
claimed/running + expired lease
        ↓
retry_wait
        ↓
worker_owner = None
worker_lease_expires_at = None
available_at = now
        ↓
下一次 Durable Frontier Claim
```

之后继续执行原有的 failed Execution Recovery Domain，不创建第二套 Recovery / Retry 算法。

## fencing 不变量

- Frontier lease 回收本身不递增 `attempt`。
- 下一次成功 `claim_next_frontier()` 才递增 Frontier fencing generation。
- Execution ownership 不由 Frontier recovery 直接抢占；Worker Claim 仍负责校验 Execution ownership / lease，并在必要时产生新的 Execution fencing generation。
- 旧 Worker 使用旧 Frontier attempt 或旧 Execution generation 写入时必须继续被现有 fencing guard 拒绝。

## 统计

`WorkflowRecoveryScanResult` 新增 `expired_frontiers`，用于记录本轮被回收的 Durable Frontier 数量，不把正常 lease recovery 计为 Execution Recovery failure。

## 测试范围

新增 Unit Test 覆盖：

- Scheduler 每轮调用 Frontier recovery；
- recovery 使用当前扫描时间和 scan limit；
- 回收数量进入 `expired_frontiers`；
- 原有 failed Execution Recovery 测试通过 monkeypatch 隔离 Frontier recovery primitive。

当前按项目开发策略不执行 Full Regression / Real API / E2E。当前环境未执行 pytest，因此不声明 Unit Test PASS。
