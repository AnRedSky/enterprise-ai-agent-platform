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
- Durable Frontier expired-lease recovery：过期 `claimed` / `running` Frontier 仅在关联 Execution ownership 同时失效时回收为 `retry_wait`：✅
- Durable Frontier Execution-aware Claim：Claim 在同一数据库事务内校验关联 Execution ownership / fencing eligibility，排除不可消费 Execution：✅
- Durable Frontier Runtime Entry Contract：统一支持新 Execution 与同 owner 后继 Frontier：✅
- Durable Frontier completed-Node Resume：线性 Workflow Recovery 后过滤已完成 Node，DAG 继续使用既有 Planner / Executor：✅
- Durable Frontier Retry Budget Resume：Node / Workflow retry budget 从 Durable facts 恢复：✅
- Durable Frontier Checkpoint Continuation：completed Node filtering 与 terminalization 已接入 Runtime 主入口：✅
- Durable Frontier Multi-frontier Completion Boundary：Branch Node facts 与 Frontier completion Checkpoint 单一持久化入口：✅
- Durable Frontier Completion Contract Hardening：`frontier_completed` 强制 Execution-level snapshot：✅
- Durable Frontier Terminal Execution Recovery Guard：terminal Execution 的旧 Frontier 不得重新激活：✅
- Durable Checkpoint Execution Lifecycle Guard：Checkpoint 写入再次校验锁定后的 Execution status：✅
- Durable Frontier Identity Canonicalization：并行 Node 集合按规范化 identity 收敛：✅
- Durable Frontier Terminalization Transaction Boundary：Frontier、Checkpoint、Execution completed、Next Frontier 统一事务提交：✅
- Durable Frontier Terminalization Ownership Recheck：terminalization 前重新验证 Frontier / Execution owner 与 fencing generation：✅
- Durable Frontier Duplicate Completion Convergence：重复 completion 必须收敛到已有 Durable facts：✅
- Durable Frontier Recovery Execution Lease Guard：Frontier lease 过期但 Execution lease 有效时禁止 Recovery：✅
- Durable Frontier Claim Head-of-Line Guard：blocked tenant 不再阻塞其他可执行 tenant：✅
- Durable Frontier Failure Terminalization Transaction Boundary：Failure retry/failed 与 Execution failed 统一补偿事务：✅
- Durable Frontier Completion Source Binding：`frontier_completed` Checkpoint 显式绑定 source Frontier，重复 completion 不再按 Execution 下最新 Checkpoint 猜测来源；历史未绑定事实不启发式回填：✅
- **Durable Frontier Recovery Multi-frontier Re-entry：Recovery 同时释放同一 Execution 的多个过期 Frontier 后，首个 Claim 取得 Execution ownership，后续 Frontier 允许复用同一 Worker epoch，不再因 `pending + current owner` 被错误阻塞：✅ 本轮**

## 当前实现边界

```text
DAG Planner
  ↓
WorkflowFrontierIdentity
  ├── execution + version + decision fingerprint
  └── canonical Node-set identity key
  ↓
complete_frontier_with_checkpoint()
  ├── duplicate completion → exact source Frontier durable facts
  ├── current Frontier → completed
  ├── terminal Execution → completed（终态）
  ├── source-bound frontier_completed Checkpoint
  └── deterministic Next Frontier（非终态）
  ↓
唯一 COMMIT / ROLLBACK
  ↓
Execution-aware Worker Claim
  ↓
Execution Ownership / Fencing
  ├── fresh pending Execution → acquire + increment epoch
  ├── recovered pending + current owner → reuse epoch
  └── expired foreign owner → reacquire + increment epoch
  ↓
Unified Runtime Entry
  ↓
Durable Resume Runtime Adapter
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
Recovery re-entry
        ↓
Concurrent multi-frontier Claim
        ↓
Execution epoch reuse / reacquisition
        ↓
Duplicate consumption guard
        ↓
Success / Failure terminalization
        ↓
Replay convergence
        ↓
Phase 2.7 主线完成
```

核心不变量：

- completed / failed / cancelled Execution 不得重新产生可消费 Frontier；
- 旧 Worker lease 到期只能回收仍属于可恢复 Execution 的 Frontier；
- Frontier lease 过期但 Execution lease 仍有效时不得 Recovery；
- Recovery 不得改变已经 terminalize 的 Execution 状态；
- Checkpoint 的 `execution_status` 必须与锁定后的当前 Execution status 一致；
- Next Frontier 的 deterministic identity 与 tenant / workflow version / execution lineage 必须继续保持单一事实来源；
- 同一 Execution / Version / Decision 下，等价并行 Node 集合必须收敛到同一个 Frontier identity；
- stale Worker 不得在 terminalization 或 Recovery transaction 之外写入新的 durable fact；
- 终态 Frontier 的 Frontier、Checkpoint、Execution terminalization 必须共享同一数据库事务；
- 终态 Frontier terminalization 前必须再次证明 Frontier owner、Execution owner 与 fencing generation 属于同一 Worker epoch；
- 已提交 Frontier 的重复 completion 必须精确绑定其 source Frontier 的 Durable Checkpoint / Next Frontier；payload drift、缺失绑定 Checkpoint 或缺失 Next Frontier 必须拒绝收敛；
- Recovery 只有在 Frontier lease 与关联 Execution ownership 同时失效后才能把 Frontier 重新放入 retry 队列；
- Worker tenant candidate 必须与实际 Frontier Claim 使用相同的 Execution eligibility 规则；
- Durable Frontier failure 的 Frontier retry/failed 与 Execution failed 必须共享同一补偿事务；
- `frontier_completed` Checkpoint 必须绑定 source Frontier，不得从同一 Execution 下其他 Frontier 的最新 completion fact 推断当前 Frontier 的幂等事实；
- **同一 Execution Recovery 后存在多个 retry_wait Frontier 时，当前 Worker 已取得 pending Execution ownership 后，后续 Frontier 必须复用同一 worker_attempt，不得再次递增 fencing generation，也不得被 pending 状态阻塞。**

## 本轮交付

- `backend/app/services/workflow_worker/frontier_runtime.py`
- `backend/app/services/workflow/frontier_repository.py`
- `backend/tests/unit/test_frontier_recovery_reentry.py`
- `docs/PROJECT_STATUS.md`
- `docs/04-errors/2026-08-27-frontier-recovery-multi-frontier-reentry.md`

**Unit Test：本轮仅实现测试代码，当前环境未执行 pytest，因此不记录 PASS。**
