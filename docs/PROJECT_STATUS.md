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
- **Durable Frontier Multi-frontier Completion Boundary：Branch Node facts 与 Frontier completion Checkpoint 现在只保留一个正式持久化入口，避免共享 Runtime helper 与 Durable Frontier progression 重复追加 `frontier_completed`：✅**
- **Durable Frontier Completion Contract Hardening：`frontier_completed` 在统一 progression primitive 内强制保持 Execution-level snapshot，禁止混入 Node identity/status/input/output：✅**
- **Durable Frontier Terminal Execution Recovery Guard：过期 Frontier 回收现在只允许关联 Execution 仍为 `pending/running` 时进入 `retry_wait`，completed/failed/cancelled Execution 的旧 Frontier 不再被 Recovery 重新激活：✅**
- **Durable Checkpoint Execution Lifecycle Guard：Checkpoint durable write 在锁定 Execution 后再次校验当前 Execution status 与快照声明一致；stale Worker 不得在 terminalization 后追加旧的 `running/pending` durable fact：✅**
- **Durable Frontier Identity Canonicalization：并行 Frontier identity key 现在对 Node 集合进行规范化排序，同一 Execution / Version / Decision 下仅因 Planner 遍历顺序不同不会生成第二个逻辑 Frontier：✅**
- **Durable Frontier Terminalization Transaction Boundary：终态 Frontier 不再通过会提前 `commit()` 的普通 Execution transition 完成 terminalization；Frontier、`frontier_completed` Checkpoint、Execution `completed` 与 Next Frontier 现在由同一 progression transaction 统一提交或回滚：✅**
- **Durable Frontier Terminalization Ownership Recheck：终态 Frontier 在 Execution terminalization 前再次锁定并校验当前 Worker owner / fencing generation，防止 Frontier 已被占有但 Execution owner 已变更时旧 Worker 结束 Execution：✅ 本轮**

## 当前实现边界

```text
DAG Planner
  ↓
WorkflowFrontierIdentity
  ├── execution + version + decision fingerprint
  └── canonical Node-set identity key
  ↓
complete_frontier_with_checkpoint()
  ├── current Frontier → completed
  ├── terminal Execution → completed（终态）
  ├── one frontier_completed Checkpoint
  └── deterministic Next Frontier（非终态）
  ↓
唯一 COMMIT / ROLLBACK
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
Recovery / Replay
```

## 当前开发策略

**继续暂停完整测试流程，优先完成全部主线任务。** 当前仅实现 Unit Test，不执行 pytest、Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance；全部主线生产代码完成后，再统一启动本地测试与验收。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造测试结果。

## 下一主线

继续收口：

```text
Next Frontier deterministic identity
        ↓
Execution terminalization
        ↓
Expired Frontier Recovery
        ↓
Worker Claim / Fencing
        ↓
Recovery re-entry
        ↓
Replay convergence
        ↓
Phase 2.7 主线完成
```

核心不变量：

- completed / failed / cancelled Execution 不得重新产生可消费 Frontier；
- 旧 Worker lease 到期只能回收仍属于可恢复 Execution 的 Frontier；
- Recovery 不得改变已经 terminalize 的 Execution 状态；
- Checkpoint 的 `execution_status` 必须与锁定后的当前 Execution status 一致；
- Next Frontier 的 deterministic identity 与 tenant / workflow version / execution lineage 必须继续保持单一事实来源；
- 同一 Execution / Version / Decision 下，等价并行 Node 集合必须收敛到同一个 Frontier identity；
- stale Worker 不得在 terminalization 或 Recovery transaction 之外写入新的 durable fact；
- **终态 Frontier 的 Frontier、Checkpoint、Execution terminalization 必须共享同一数据库事务，不允许普通 commit 型状态入口提前提交；**
- **终态 Frontier terminalization 前必须再次证明 Frontier owner、Execution owner 与 fencing generation 属于同一 Worker epoch。**

## 本轮交付

- `backend/app/services/workflow/frontier_progression.py`
- `backend/tests/unit/test_frontier_terminalization_atomicity.py`
- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_7.md`
- `docs/04-errors/2026-08-27-frontier-terminalization-transaction-boundary.md`

**Unit Test：本轮仅实现测试代码，当前环境未执行 pytest，因此不记录 PASS。**
