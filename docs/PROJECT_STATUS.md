# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.7 Advanced Workflow Orchestration，主线正在完成 Recovery / Replay Closure。
- Phase 2.7 已完成 Conditional Branching、Durable Frontier Scheduling、Scheduler → Worker → Runtime、Retry Scheduling、Frontier → Checkpoint 原子推进、Runtime failure convergence、Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor contract、tenant boundary、Checkpoint lineage、Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker Checkpoint late-write guard、Node → Checkpoint fencing propagation、Checkpoint durable write boundary、Multi-frontier Join Recovery、Replay Decision Convergence。
- **已完成 Multi-frontier Runtime 的 Execution-level `frontier_completed` Checkpoint 持久化：所有 Branch 执行成功并完成 Node-level Checkpoint 后，Runtime 才写入 merged state 的 frontier completion durable boundary，并继续使用 Worker fencing 与当前事务。**
- **Recovery / Replay lifecycle closure 已完成：已有但未完成 Bootstrap 的 pending Resume 现在可以在 Source Execution 锁内安全重新 Bootstrap，结果明确记录为 `reconciled`，不创建第二个 Resume。**
- **Recovery Scheduler 已将 `reconciled` 作为成功恢复结果统计，避免合法自愈被记录为 failed / rejected。**
- **Scheduler Service 双循环生命周期监督已完成：Scheduled Trigger Dispatch 与 Durable Recovery Scan 任一循环异常时统一停止另一循环并传播原始异常，避免 Scheduler Service 半存活。**
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：生产实现继续收口；Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦及双循环生命周期监督均已实现。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；DAG 分支 Resume / 多-frontier Runtime 正在继续收口；Unit Test 实际 Closure 仍按本地执行结果记录。
- **DAG Next Frontier progression Contract 已完成：Checkpoint 后重新调用唯一 `WorkflowDagResumePlanner`，基于完整 completed durable facts 生成下一 Frontier 的 deterministic `WorkflowFrontierIdentity`；不创建第二套 Planner / Frontier persistence。**
- **`frontier_completed` Execution-level Checkpoint 已完成同事务幂等收敛：Runtime 与 `complete_frontier_with_checkpoint()` 双边界重复提交相同 merged-state durable fact 时复用已有 Checkpoint，不再产生重复 sequence。**
- **已完成 DAG Frontier → Durable Frontier 原子推进接线：`WorkflowDagFrontierProgressionService.complete_frontier()` 先通过唯一 Planner 生成 Next Frontier identity，再统一调用 `complete_frontier_with_checkpoint()` 完成 Frontier → Checkpoint → Next Frontier，不允许 Runtime 旁路 enqueue。**
- **已完成 Durable Frontier Worker 的后继 Frontier ownership 复用：同一 Worker 在同一 Execution 内继续消费后继 Frontier 时复用现有 Execution fencing generation；只有接管过期的其他 Worker lease 才递增 generation，避免后继 Frontier 因错误 generation 被 Checkpoint fencing 拒绝。**
- Backend 模块化整改：继续按最新治理规则推进，不作为当前主线阻塞条件。
- Frontend Phase 1.3：SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。

## Phase 2.7 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- `WorkflowDagResumePlanner` 是首次执行与 Resume 的统一 Planner，输出 completed / frontier / selected predecessor / deterministic decision fingerprint；
- Runtime Plan 直接消费 immutable Planner result，不重复执行 Planner；
- Conditional Join 与 Multi-frontier Join Recovery 只消费 Planner selected predecessor 与 durable Node facts；
- Decision Trace 对 replay payload drift 进行一致性校验，并在写入前强制执行 Replay Guard；
- Durable Frontier、Claim、lease fencing、expired lease recovery、retry scheduling、Scheduler → Worker → Runtime bridge 已完成；
- `complete_frontier_with_checkpoint()` 统一 Frontier → Checkpoint → Next Frontier 原子推进；
- Durable Resume Bootstrap 在同一事务复制 completed Node lineage、重新运行唯一 Planner、幂等入队首个 Frontier；
- Resume Source / tenant / workflow version / checkpoint sequence lineage 均有正式 guard；
- `frontier_completed` 为 Execution-level Checkpoint；
- Execution / Node / Checkpoint durable write 均受 worker generation fencing 保护；
- Multi-frontier Join Recovery 已从 durable predecessor facts 重建 merged state，并校验 `frontier_completed.state_data`；
- Multi-frontier Runtime 在所有 Branch Node-level Checkpoint 成功后追加 merged-state `frontier_completed` Execution-level Checkpoint，作为进入下一 frontier planning 的 durable boundary；
- **`WorkflowDagFrontierProgressionService` 负责把当前 frontier 完成后的 durable facts 重新交给唯一 Planner，并生成下一 Frontier identity；真正的持久化继续由 `complete_frontier_with_checkpoint()` 负责。**
- **`WorkflowDagFrontierProgressionService.complete_frontier()` 已将上述 planning 与原子持久化正式接线：Planner 不写库，Runtime 不自行 enqueue，所有 Frontier → Checkpoint → Next Frontier 持久化统一进入既有 transaction contract。**
- **`WorkflowExecutionCheckpointService.append_next_in_transaction()` 对相同 `frontier_completed` execution status / merged state / worker owner 的重复 durable boundary 进行幂等复用，避免 Runtime 与 Frontier progression 接线产生重复 Execution-level snapshot。**
- **`DurableFrontierWorkflowWorker.claim_one_frontier()` 已支持同一 Worker 在同一 running Execution 中继续领取后继 Frontier，并保持原 `worker_attempt`；外部过期 ownership 则通过新的 generation 接管。**
- Replay Decision Convergence 已将历史 Decision、frontier、selected predecessor 收敛检查提升为写入前强制边界；
- Resume lifecycle closure 已完成：完整 Resume 幂等命中必须具有 Durable Frontier；pending 且缺少 Frontier 的历史不完整 Resume 现在允许在 Source Execution 锁内幂等重新 Bootstrap。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7 Conditional Branching
  └── Conditional Branching Closure       ✅

Durable Frontier Scheduling
  ├── Durable Frontier persistence        ✅
  ├── Claim / lease / fencing             ✅
  ├── Retry Scheduling                    ✅
  ├── Scheduler → Worker → Runtime       ✅
  ├── Frontier → Checkpoint progression  ✅
  └── Runtime failure convergence        ✅

Recovery / Replay Closure
  ├── Durable Resume Bootstrap             ✅
  ├── Recovery Trace atomic transaction    ✅
  ├── Join predecessor contract            ✅
  ├── Resume tenant boundary               ✅
  ├── Resume Checkpoint lineage            ✅
  ├── Cross-Execution Replay Identity     ✅
  ├── Multi-frontier Checkpoint boundary   ✅
  ├── Execution fencing generation         ✅
  ├── stale Worker Checkpoint late-write   ✅
  ├── Node → Checkpoint fencing propagation ✅
  ├── Checkpoint durable write boundary    ✅
  ├── Multi-frontier Join Recovery         ✅
  ├── Replay decision convergence           ✅
  ├── Resume lifecycle idempotency closure  ✅
  ├── Incomplete Resume Bootstrap reconcile ✅
  ├── Multi-frontier Runtime completion checkpoint ✅
  ├── DAG Next Frontier deterministic identity      ✅
  ├── frontier_completed checkpoint idempotency      ✅
  ├── DAG Frontier → Durable Frontier atomic bridge  ✅
  └── Durable Frontier → running Execution ownership reuse ✅ 本轮

Phase 2.4 Durable Scheduler
  ├── Persistence / Runtime                ✅
  ├── API Contract / tenant / misfire      ✅
  ├── API / Scheduler process separation   ✅
  └── Dual-loop lifecycle supervision      ✅

Phase 2.4 完整 Gate / Acceptance
  └── 按当前策略暂缓，不阻塞主线开发
```

## 本轮交付与文档

- `backend/app/services/workflow_worker/frontier_runtime.py`
- `backend/tests/unit/test_durable_frontier_worker_dispatch.py`
- `docs/04-errors/2026-08-27-durable-frontier-execution-ownership-reuse.md`
- `docs/PROJECT_STATUS.md`

**Unit Test：本轮未在当前环境执行，因此不记录 PASS。完整 Gate / Acceptance 继续暂停。**
