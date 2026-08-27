# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.7 Advanced Workflow Orchestration，主线正在完成 Recovery / Replay Closure。
- Phase 2.7 已完成 Conditional Branching、Durable Frontier Scheduling、Scheduler → Worker → Runtime、Retry Scheduling、Frontier → Checkpoint 原子推进、Runtime failure convergence、Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor contract、tenant boundary、Checkpoint lineage、Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker Checkpoint late-write guard、Node → Checkpoint fencing propagation、Checkpoint durable write boundary、Multi-frontier Join Recovery、Replay Decision Convergence。
- **本轮完成 Recovery / Replay lifecycle closure：Resume 幂等命中现在必须验证对应 Resume Execution 已存在 Durable Frontier；缺失 Frontier 的不完整 Resume 不得返回 `idempotency_hit`。**
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：已完成既定实现范围，不作为当前主线阻塞条件。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；Unit Test 实际 Closure 仍按本地执行结果记录。
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
- Replay Decision Convergence 已将历史 Decision、frontier、selected predecessor 收敛检查提升为写入前强制边界；
- **Resume lifecycle closure 已完成：`WorkflowExecutionResumeContractService` 对幂等命中增加 Durable Frontier 完整性证明，防止历史不完整 Resume 永久吞掉恢复请求。**

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
  └── Resume lifecycle idempotency closure  ✅ 本轮

Recovery / Replay lifecycle closure
  └── 生产代码闭环                         ✅
      本地 Unit Test 实际执行               ← 待开发者环境执行
```

## 本轮交付与文档

- `backend/app/services/workflow/checkpoint/recovery/resume_contract.py`
- `backend/tests/unit/test_workflow_recovery_lifecycle_closure.py`
- `docs/04-errors/2026-08-27-recovery-replay-lifecycle-closure.md`
- `docs/02-phases/PHASE_2_7.md`
- `docs/PROJECT_STATUS.md`

**Unit Test：本轮未在当前环境执行，因此不记录 PASS。Recovery / Replay lifecycle closure 的生产代码已完成；下一阶段不再新增 Recovery 平行实现，转入项目剩余主线任务。**
