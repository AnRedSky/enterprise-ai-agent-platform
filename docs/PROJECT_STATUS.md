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
- **Durable Frontier Retry Budget Resume：Node `attempt` 与 Workflow Retry budget 在 Worker Recovery 后从持久化事实恢复，避免 Runtime 重启清零本地计数并绕过 Retry 上限：✅ 本轮**

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
  └── DAG Workflow → existing Planner / Executor
  ↓
WorkflowRuntime
  ↓
Node / Checkpoint durable facts
  ↓
frontier_completed
  ↓
Next Frontier
  ↓
Execution-aware Worker Claim
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
  ↓
恢复 Node / Workflow Retry budget
  ↓
跳过已完成 Node
  ↓
继续未完成 Node
```

关键不变量：

1. Frontier Claim 必须同时满足 tenant scope 与关联 Execution 的可消费状态。
2. Frontier lease 过期只回收调度权，不直接递增 `attempt`；下一次成功 Claim 才产生新的 fencing generation。
3. Recovery Scheduler 不创建新的 Execution / Frontier，不复制 Retry / Planner / Runtime 算法。
4. 同一 Worker 在同一 Execution 内继续消费后继 Frontier 时复用 Execution fencing generation；只有 lease 失效后才产生新的 generation。
5. Frontier → Checkpoint → Next Frontier 继续由统一 `complete_frontier_with_checkpoint()` 原子提交。
6. `completed` / `failed` / `cancelled` Execution 不允许再次成为 Durable Frontier Runtime 的消费入口。
7. Runtime Entry 不允许通过回退数据库状态绕过 Execution 状态机；`pending` 才执行 `pending → running`，`running + same owner` 直接继续唯一 `WorkflowRuntime`。
8. Runtime 执行期间必须由 `WorkflowWorkerLeaseGuard` 持续验证 ownership；明确 Lease Lost 后立即取消 Runtime，旧 Worker 不再提交终态。
9. 线性 Workflow Resume 必须基于当前 Execution 的 durable `completed` Node facts 跳过已成功节点；DAG Resume 继续由既有 Planner 根据完成事实决定 frontier，不得复制第二套 DAG 规划逻辑。
10. Node `attempt` 是持久化 Retry 事实；Worker Recovery 不能把 Node Retry 次数清零。
11. Workflow Retry budget 必须基于持久化 Node attempt 恢复；fencing generation 与 Retry budget 相互独立。

## 当前开发策略

暂停完整测试流程，只保留 Unit Test 实现作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test PASS。

## 下一主线

下一步继续收口：

```text
Durable Resume Runtime
  ↓
Node Retry / Lease Recovery
  ↓
持久化 Node attempt
  ↓
Workflow Retry budget
  ↓
Checkpoint continuation
  ↓
frontier completion
  ↓
Next Frontier
```

重点继续检查 Node Retry 与 Frontier Retry 的边界：Node transient failure 必须留在同一 Execution 内按 Node policy 重试；Worker Lease Lost 必须进入 Frontier Recovery 并产生新的 fencing generation；两种恢复不能互相重置 Retry budget，也不能重复执行已经成功 Checkpoint 的 Node。

## 本轮交付

- `backend/app/services/workflow_worker/resume_runtime.py`
- `backend/tests/unit/test_durable_resume_runtime.py`
- `docs/04-errors/2026-08-27-durable-frontier-retry-budget-resume.md`
- `docs/PROJECT_STATUS.md`

**Unit Test：本轮只实现/更新测试代码，当前环境未执行 pytest，因此不记录 PASS。**
