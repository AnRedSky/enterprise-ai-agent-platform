# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.7 Advanced Workflow Orchestration，主线正在完成 Durable Frontier / Recovery / Replay Closure。
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：生产实现继续收口；Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦及双循环生命周期监督均已实现。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；DAG 分支 Resume / 多-frontier Runtime 正在继续收口。
- Phase 2.7 Conditional Branching、Durable Frontier Scheduling、Recovery / Replay Closure 的核心生产链路持续收口。

## 已完成的 Recovery / Frontier 主线

- Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor contract、tenant / version / checkpoint lineage guard：✅
- Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker late-write guard、Node → Checkpoint fencing propagation：✅
- Multi-frontier Join Recovery、Replay Decision Convergence、Resume lifecycle idempotency、Incomplete Resume Bootstrap reconcile：✅
- Multi-frontier Runtime `frontier_completed` Execution-level Checkpoint：✅
- DAG Next Frontier deterministic identity：✅
- `frontier_completed` checkpoint idempotency：✅
- DAG Frontier → Durable Frontier atomic progression bridge：✅
- Durable Frontier → same-Execution Worker ownership reuse：✅
- **Durable Frontier expired-lease recovery 已接入统一 Recovery Scheduler：过期 `claimed` / `running` Frontier 会被原子回收为 `retry_wait`，清除旧 Worker ownership，并重新进入 Durable Claim 队列；Recovery Scheduler 同一轮继续处理 failed Execution。**

## 当前实现边界

```text
DAG Planner
  ↓
WorkflowFrontierIdentity
  ↓
complete_frontier_with_checkpoint()
  ↓
Durable Frontier
  ↓
Worker Claim / Fencing
  ↓
Workflow Runtime
  ↓
Node Checkpoint
  ↓
frontier_completed
  ↓
Next Frontier
  ↓
Worker Claim / Fencing
  ↓
...

Failure / Worker lease expiry
  ↓
Durable Frontier Recovery Scheduler
  ↓
retry_wait + ownership release
  ↓
下一次 Claim 产生新的 Frontier fencing generation
  ↓
Runtime Resume
```

关键不变量：

1. Frontier lease 过期只回收调度权，不直接递增 `attempt`；下一次成功 Claim 才产生新的 fencing generation。
2. Recovery Scheduler 不创建新的 Execution / Frontier，不复制 Retry / Planner / Runtime 算法。
3. 同一 Worker 在同一 Execution 内继续消费后继 Frontier 时复用 Execution fencing generation。
4. 外部 Worker lease 过期后才允许新的 Worker 接管 Execution 并递增 generation。
5. Frontier → Checkpoint → Next Frontier 继续由统一 `complete_frontier_with_checkpoint()` 原子提交。

## 当前开发策略

暂停完整测试流程，只保留 Unit Test 实现作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test PASS。

## 下一主线

下一步继续收口：

```text
expired Frontier recovery
  ↓
new Worker Claim / fencing generation
  ↓
Runtime resume from durable Node / Checkpoint facts
  ↓
frontier completion
  ↓
Next Frontier
```

重点验证 Retry / lease-expiry 后的 Resume 是否始终消费正确的 durable completed-node facts，并确保旧 Worker 无法通过旧 generation 写入 Checkpoint 或 Frontier 终态。

## 本轮交付

- `backend/app/services/workflow_scheduler/recovery.py`
- `backend/tests/unit/test_workflow_recovery_scheduler.py`
- `docs/04-errors/2026-08-27-expired-frontier-recovery-scheduler.md`
- `docs/PROJECT_STATUS.md`

**Unit Test：本轮只实现/更新测试代码，当前环境未执行 pytest，因此不记录 PASS。**
