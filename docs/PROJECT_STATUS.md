# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.7 Advanced Workflow Orchestration，主线已从 Conditional Branching Closure 转入 Durable Frontier Scheduling，并继续收敛 Recovery / Replay Closure。
- 本轮完成：**Multi-frontier Join Recovery**；Recovery Bootstrap 在进入 Join frontier 前，使用 Planner selected predecessor 与 completed Node durable outputs 重新计算 merged state，并校验最新 `frontier_completed` Execution-level Checkpoint state，防止 Recovery 使用漂移的 merged snapshot。
- Phase 2.7 当前已完成 Conditional Branching、Durable Frontier 持久化/Claim/Fencing/Recovery、Scheduler/Worker 实际接入、Retry Scheduling、Frontier → Checkpoint → Next Frontier 原子推进、Runtime/Planner progression wiring、Runtime failure convergence、Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor Contract、tenant boundary、Checkpoint lineage、Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker Checkpoint late-write guard、Node → Checkpoint fencing propagation、Checkpoint durable write boundary 以及 Multi-frontier Join Recovery。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；Unit Test 实际 Closure 仍按本地执行结果记录。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**

## Phase 2.7 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口，DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`，并限制深度、节点数及 JSON 类型边界；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default、重复 edge、未知 Node 与循环图；
- Conditional frontier 按 Definition 顺序确定性选择，多个条件同时命中可形成并行 frontier；
- `WorkflowDagResumePlanner` 是首次执行与 Resume 的统一 Planner，输出 completed / frontier / selected predecessor / deterministic decision fingerprint；
- Runtime Plan 直接消费 immutable Planner result，不重复执行 Planner；
- Conditional Join 只消费 Planner selected predecessor，并拒绝未知/重复 predecessor；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才生成 merged state / `join_ready=true`；
- Decision Trace 使用 execution + tenant + workflow version + trace + fingerprint 作为幂等 identity，并对 replay payload drift 做一致性校验；
- `WorkflowFrontierIdentity`、Frontier lifecycle、PostgreSQL durable frontier、tenant/key uniqueness、Claim `FOR UPDATE SKIP LOCKED`、worker lease fencing、expired lease recovery、retry scheduling 均已完成；
- Scheduler → Durable Frontier → Worker → Runtime 已完成实际桥接，默认 `WorkflowWorker` 为 `PlannerDrivenDurableFrontierWorkflowWorker`；
- Worker 成功路径统一调用 `complete_frontier_with_checkpoint()`，由单一 progression primitive 负责 Frontier fencing、Checkpoint append 与 Next Frontier enqueue；
- Runtime 异常统一进入 Frontier Retry / Failed，retry exhausted 时 Frontier 与 Execution 一起进入 `failed`；
- Durable Resume Bootstrap 在同一外层事务内复制 completed Node lineage、重新运行唯一 Planner、幂等入队首个 Frontier；
- Resume Source / Resume tenant、workflow version、checkpoint sequence lineage 均有正式 guard；
- `frontier_completed` 强制为 Execution-level Checkpoint，`node_id` 与 `node_status` 必须为空；
- Execution `worker_owner + worker_attempt` fencing 已延伸到 Execution / Node / Checkpoint durable write，旧 generation 不得继续写入；
- Checkpoint durable write boundary 在真正落库前再次拒绝 Node/Execution-level 混合事实；
- **Multi-frontier Join Recovery 已完成**：`WorkflowDagJoinRecoveryService` 复用唯一 Join readiness / State Merge 能力，在 Resume Bootstrap 中校验 `frontier_completed.state_data` 与 Planner selected predecessor durable outputs 的重新计算结果；drift、缺失 predecessor 或非法 predecessor 立即拒绝 Recovery。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7 Conditional Branching
  └── Conditional Branching Closure     ✅

Durable Frontier Scheduling
  ├── Frontier deterministic identity   ✅
  ├── Frontier lifecycle contract       ✅
  ├── PostgreSQL Durable Frontier       ✅
  ├── Tenant/key uniqueness             ✅
  ├── Idempotent Frontier enqueue       ✅
  ├── Claim repository                  ✅
  ├── Worker lease fencing              ✅
  ├── Expired lease recovery            ✅
  ├── Scheduler → Frontier enqueue      ✅
  ├── Frontier → Worker claim           ✅
  ├── Worker → Runtime bridge           ✅
  ├── Frontier lease heartbeat          ✅
  ├── Retry scheduling                  ✅
  ├── Frontier → Checkpoint progression ✅
  ├── Next Frontier idempotent enqueue  ✅
  ├── Runtime/Planner progression wiring ✅
  ├── Runtime failure convergence       ✅
  └── Unified success persistence path  ✅

Recovery / Replay Closure
  ├── Durable Resume Bootstrap           ✅
  ├── Recovery Trace atomic transaction  ✅
  ├── Join predecessor contract          ✅
  ├── Resume tenant boundary             ✅
  ├── Resume Checkpoint lineage           ✅
  ├── Cross-Execution Replay Identity    ✅
  ├── Multi-frontier Checkpoint boundary  ✅
  ├── Execution fencing generation       ✅
  ├── stale Worker Checkpoint late-write  ✅
  ├── Node → Checkpoint fencing propagation ✅
  ├── Checkpoint durable write boundary   ✅
  ├── Multi-frontier Join Recovery        ✅ 本轮
  └── Replay decision convergence         ← 下一任务
          ↓
  最终 Recovery / Replay lifecycle closure

继续主线直到全部任务完成。
```

## 本轮交付与文档

- `backend/app/services/workflow/checkpoint/recovery/dag_join_recovery.py`
- `backend/app/services/workflow/checkpoint/recovery/resume_bootstrap.py`
- `backend/app/services/workflow/checkpoint/recovery/__init__.py`
- `backend/tests/unit/test_workflow_dag_join_recovery.py`
- `docs/04-errors/2026-08-27-multi-frontier-join-recovery.md`
- `docs/02-phases/PHASE_2_7.md`

**Unit Test：本轮未在本地执行，因此不记录 PASS。下一主线为 Replay decision convergence，不停留在文档总结。**
