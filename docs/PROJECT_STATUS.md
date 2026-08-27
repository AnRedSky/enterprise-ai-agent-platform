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
- Durable Frontier expired-lease recovery 已接入统一 Recovery Scheduler：过期 `claimed` / `running` Frontier 会被原子回收为 `retry_wait`，清除旧 Worker ownership，并重新进入 Durable Claim 队列；Recovery Scheduler 同一轮继续处理 failed Execution：✅
- Durable Frontier Execution-aware Claim：Claim 在同一数据库事务内校验关联 Execution ownership / fencing eligibility，排除 completed / failed / cancelled Execution，避免不可消费 Frontier 形成调度头阻塞：✅
- Durable Frontier Runtime Entry Contract：统一支持 `pending + owner` 新 Execution 与 `running + same owner + fencing generation` 后继 Frontier；Node Runtime 仍唯一委托 `WorkflowRuntime`，LeaseGuard 继续负责 ownership loss abort：✅
- Durable Frontier completed-Node Resume：线性 Workflow 在 Retry / Lease Recovery 后过滤已成功持久化 Node，DAG Workflow 继续使用既有 Planner / Executor：✅
- Durable Frontier Retry Budget Resume：Node `attempt` 与 Workflow Retry budget 在 Worker Recovery 后从持久化事实恢复，避免 Runtime 重启清零本地计数并绕过 Retry 上限：✅
- **Durable Frontier Checkpoint Continuation：Resume Runtime 主入口已实际应用 completed-Node filtering；全部线性 Node 已完成时直接 terminalize Execution，避免 Recovery 后 Node replay：✅**
- **Durable Frontier Multi-frontier Completion Boundary：Branch Node facts 与 Frontier completion Checkpoint 现在只保留一个正式持久化入口，避免共享 Runtime helper 与 Durable Frontier progression 重复追加 `frontier_completed`：✅ 本轮**

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
Execution-aware Worker Claim
  ↓
Execution Ownership / Fencing
  ↓
Unified Runtime Entry
  ├── pending + owner → running
  └── running + same owner → continue
  ↓
Durable Resume Runtime Adapter
  ├── linear Workflow → skip completed Node facts
  ├── Node Retry → restore persisted attempt budget
  ├── Workflow Retry → restore persisted retry budget
  └── DAG Workflow → existing Planner / Executor
  ↓
WorkflowRuntime
  ↓
Node / Checkpoint durable facts
  ↓
frontier_completed
  ↓
Next Frontier
```

## 当前开发策略

暂停完整测试流程，只保留 Unit Test 实现作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test PASS。

## 下一主线

下一步继续收口 Frontier completion / Next Frontier 后的 Recovery consistency，重点检查 Multi-frontier Branch Node durable completion、`frontier_completed` Execution-level snapshot、Next Frontier deterministic identity 与 Worker lease/fencing 在失败、重试、Recovery 及重复消费窗口下是否保持单一事实来源。

```text
Multi-frontier Branch
  ↓
NodeExecution durable completion
  ↓
唯一 frontier_completed Checkpoint
  ↓
Next Frontier
  ↓
Worker Claim / Fencing
  ↓
Recovery / Replay
```

重点检查：同一 Frontier 不得产生两个 completion Checkpoint；Next Frontier 不得因为重复 completion 被重复执行；stale Worker 不得在 completion transaction 外写入新的 durable fact；Retry / Lease Recovery 不得重置已经持久化的 Node attempt 与 Workflow Retry budget。

## 本轮交付

- `backend/app/services/workflow_worker/durable_frontier_execution.py`
- `backend/tests/unit/test_durable_frontier_execution.py`
- `docs/04-errors/2026-08-27-durable-frontier-checkpoint-continuation.md`
- `docs/02-phases/PHASE_2_7.md`
- `docs/PROJECT_STATUS.md`

**Unit Test：本轮只实现/更新测试代码，当前环境未执行 pytest，因此不记录 PASS。**