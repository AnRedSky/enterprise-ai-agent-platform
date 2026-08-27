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
- Durable Frontier Recovery Multi-frontier Re-entry：Recovery 同时释放同一 Execution 的多个过期 Frontier 后，首个 Claim 取得 Execution ownership，后续 Frontier 允许复用同一 Worker epoch，不再因 `pending + current owner` 被错误阻塞：✅
- Durable Frontier Stale Lease Completion Guard：Frontier 最终 completion/failure transition 同时校验 owner、attempt 与未过期 Worker lease，阻断 lease 已过期但 Recovery 尚未完成清理时的旧 Worker 写入：✅
- Durable Frontier Execution Worker Epoch Binding：Progression 在最终 durable write 前锁定关联 Execution，并使用 `Execution.worker_attempt` 作为 Worker fencing epoch；严格区分 Execution epoch 与 Frontier consumption attempt，Next Frontier 的 Checkpoint 不再错误使用 Frontier attempt 作为 Execution fencing generation：✅
- Durable Checkpoint Worker Lease Write Guard：带 Worker fencing 参数的 Checkpoint durable write 在锁定 Execution 后再次证明 owner、worker epoch 与未过期 lease，阻断 stale Worker 在 Node-level Checkpoint 边界产生 durable fact：✅
- Durable Frontier / Execution Atomic Lease Heartbeat：Frontier heartbeat 同一短事务内同时续租关联 Execution 与 Frontier；任一层 owner、status、fencing 或 lease 失效均整体回滚，禁止形成跨层 lease 不一致窗口：✅
- Durable Frontier Base Runtime Lease-Lost Abort：基础 Durable Frontier Worker 在 atomic heartbeat 发现 ownership 失效时取消当前 Runtime task，避免旧 Worker 继续执行：✅
- Durable Frontier Planner Runtime Lease-Lost Abort：Planner/DAG Worker 显式将当前 `execute_frontier()` task 传递给 heartbeat；lease loss 后取消 Planner Runtime，`CancelledError` 不进入普通 failure convergence，当前事务 rollback 后交由 Recovery 接管：✅
- Durable Frontier Failure Convergence Ownership Guard：failure retry / failed convergence 在任何 Frontier transition、retry scheduling 或 Execution terminalization 前重新证明 Execution owner 与有效 lease；stale Worker 不得跨层终止其他 Worker 持有的 Execution：✅
- Durable Frontier Runtime Consumption Guard：Runtime 真正执行 Node 前重新锁定 Frontier 与 Execution，证明当前 Worker owner、Frontier attempt、两层 active lease 与可执行状态；Claim 后发生 ownership 转移、回收或 terminalization 的 stale task 不得继续消费：✅ 本轮

## 当前实现边界

```text
DAG Planner
  ↓
WorkflowFrontierIdentity
  ├── execution + version + decision fingerprint
  └── canonical Node-set identity key
  ↓
Execution-aware Worker Claim
  ├── fresh pending Execution → acquire + increment epoch
  ├── recovered pending + current owner → reuse epoch
  └── expired foreign owner → reacquire + increment epoch
  ↓
Runtime Consumption Guard
  ├── Frontier owner + attempt + active lease
  └── Execution owner + active lease + pending/running
  ↓
Atomic Worker Lease Heartbeat
  ├── Frontier owner + attempt + active lease
  └── Execution owner + worker epoch + active lease
  ↓
Unified Runtime Entry
  ↓
WorkflowRuntime / Planner Runtime
  ├── lease loss → cancel Runtime
  └── cancellation → rollback, no normal failure convergence
  ↓
Node / Checkpoint durable facts
  ├── Checkpoint → Execution worker epoch + active lease
  └── stale Worker → rejected
  ↓
Success / Failure Convergence
  ├── success → complete_frontier_with_checkpoint()
  └── failure → ownership/lease guard → retry_wait / failed
  ↓
Frontier / Checkpoint / Execution progression
  ↓
唯一 COMMIT / ROLLBACK
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
Concurrent multi-frontier Claim
        ↓
Duplicate consumption guard
        ↓
Success / Failure terminalization
        ↓
Replay convergence
        ↓
Phase 2.7 主线完成
```

其中 Runtime Consumption Guard 已完成，下一步重点转向 **Concurrent multi-frontier Claim 的同一 Execution 并发边界** 与最终 Replay convergence。

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
- 同一 Execution Recovery 后存在多个 retry_wait Frontier 时，当前 Worker 已取得 pending Execution ownership 后，后续 Frontier 必须复用同一 worker_attempt，不得再次递增 fencing generation，也不得被 pending 状态阻塞；
- Frontier terminal transition 除 owner 与 attempt 外必须证明 `worker_lease_expires_at > now`，lease 已失效的旧 Worker 不得完成或失败 Frontier；
- Execution `worker_attempt` 是 Worker ownership epoch；Frontier `attempt` 仅是 Frontier consumption attempt，二者禁止互相替代；Progression 写入 Checkpoint 时必须使用锁定后的 Execution epoch；
- 带 Worker fencing 参数的 Node-level Checkpoint 写入必须同时证明 Execution owner、worker epoch 与未过期 lease；stale Worker 不能仅凭 owner + epoch 写入新的 Node durable fact；
- Worker heartbeat 必须在同一短事务内续租 Frontier 与关联 Execution；任一层续租失败必须整体 rollback，不得形成 Frontier 有效而 Execution 失效或反向的不一致 lease pair；
- Frontier / Execution heartbeat 丢失 ownership 后必须取消当前 Planner / Node Runtime；lease loss 不得作为普通业务 failure 进入 retry / failed convergence；
- Failure convergence 在进入 retry / failed 前必须重新证明 Execution owner 与有效 lease；stale Worker 不得通过 failure path 改变其他 Worker 的 Execution 生命周期；
- Runtime Node execution 前必须重新证明 Frontier 与 Execution consumption ownership；stale task 不得仅凭 Claim 阶段的内存快照继续执行。

## 本轮交付

- `backend/app/services/workflow_worker/durable_frontier_execution.py`
- `backend/tests/unit/test_frontier_terminalization_atomicity.py`
- `docs/PROJECT_STATUS.md`
- `docs/04-errors/2026-08-27-durable-frontier-failure-convergence-ownership.md`

**测试：本轮未执行 pytest、集成测试、本地手动测试或 E2E；不得记录 PASS。**
