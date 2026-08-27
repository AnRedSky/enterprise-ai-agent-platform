# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：Phase 2.7 Advanced Workflow Orchestration，主线已从 Conditional Branching Closure 转入 Durable Frontier Scheduling。
- 本轮已完成：**Recovery / Replay Checkpoint Node Fact lineage 收敛**；Automatic Recovery 与 Resume Contract 在生成 Recovery Candidate 前统一使用 `latest_recovery_fact()`，强制 Node-level Checkpoint 与同一 Execution 的 Durable Node Fact 在 status / attempt / output_data 上保持一致。
- Durable Recovery Resume Trace 原子事务闭环已完成；Automatic Recovery 现在将 Resume 创建、completed Node lineage、首个 Durable Frontier 与 `recovery.trace_linked` 在同一外层事务中提交，避免恢复审计事实与 Resume durable state 分裂。
- Durable Resume 现在固定 Source Workflow Version，使用 `execution_id + checkpoint_sequence` 生成确定性 Resume idempotency key；并通过 Resume Bootstrap 计算首个 Planner frontier。
- Scheduler → Durable Frontier → Worker → Runtime 实际桥接已完成；Scheduled Trigger 创建 pending Execution 时同步创建首个 Durable Frontier，默认 Worker 以 Frontier 为调度入口并复用唯一 WorkflowExecution Runtime。
- Runtime Durable Commit Ownership：**已完成；Runtime NodeExecution / Checkpoint transition 使用 `commit=False`，由外层 Execution transition 统一提交；直接调用方默认保持 `commit=True` 兼容。**
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching Closure 已完成其当前实现范围，Durable Frontier 已完成持久化、Claim/Fencing/Recovery、Scheduler/Worker 实际接入、Retry Scheduling、Frontier → Checkpoint → Next Frontier 原子推进、Runtime/Planner progression wiring、Runtime 异常路径收敛、成功路径统一持久化、Durable Resume Bootstrap、Recovery Trace 原子事务闭环、Join predecessor Contract、Resume tenant boundary 以及 Recovery Checkpoint Node Fact lineage guard。**

## Phase 2.7 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- 已实现深度 / 节点数上限；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default 数量、重复 edge、未知 Node 和循环图；当前第一版 DAG Contract 要求单 root；
- Conditional frontier 按 Definition 顺序确定性选择并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts，Join readiness 不复制条件解析；
- 首次执行与 Resume 均通过统一 DAG Planner；
- Conditional Join 只消费 Planner selected predecessor，并拒绝未知或重复 predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Resume Bootstrap 开始时强制 Source / Resume `tenant_id` 一致，Source completed Node 与 Resume lineage 查询均通过 `WorkflowExecution` JOIN 携带 tenant scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`，并在恢复候选生成前调用 `latest_recovery_fact()` 校验 Node-level Checkpoint 的 Durable Fact 完整性；
- Resume Contract 在 Source Execution row lock 后再次强制使用 `locked_execution.tenant_id` 查询最新 Recovery Fact；
- Resume Contract 创建 Resume 时使用 `commit=False`，随后由 `WorkflowExecutionResumeBootstrapService` 在同一事务复制 completed Node lineage 并 enqueue 首个 Frontier；
- Resume Contract 支持 caller-owned commit，Automatic Recovery 将 Resume、Bootstrap 与 trace link 放入同一外层事务；
- Resume Bootstrap 固定 Source Workflow Version，不复制新的 Runtime/Planner；DAG 使用 `WorkflowDagResumePlanner` 计算首个 frontier，无 Edge 顺序 Workflow 按 Definition 顺序选择下一个未完成 Node；
- Runtime 持久化 `workflow.dag.frontier_decided` decision metadata；
- Planner 生成 deterministic `decision_fingerprint`，同时绑定 completed Node facts、条件 source state、frontier 与 selected predecessor；
- Runtime Plan 显式携带 Planner fingerprint，Runtime 不再复制 Decision identity 计算逻辑；
- Decision Trace 不保存业务 state_data，只保存 fingerprint 和可审计的节点选择 metadata，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state / `join_ready=true`；
- 同一 Recovery trace 下相同 durable completed facts 必须保持相同 `decision_fingerprint`，Replay Guard 对不一致 Decision 立即失败；
- DAG Decision Trace 使用 execution + tenant + workflow version + trace + decision fingerprint 作为幂等 identity；
- Checkpoint 自动序号分配锁定目标 `WorkflowExecution` 后读取最大 sequence；
- Checkpoint Node fact completeness、Recovery Trace lineage、Decision rebuild、Trace lineage continuity、payload drift guard、fingerprint JSON boundary、single DAG planning boundary、tenant boundary、Resume idempotency lineage/key determinism、SAVEPOINT、Recovery Commit Ownership、Runtime Durable Commit Ownership 与 Recovery latest Node Fact guard 均已完成；
- `WorkflowFrontierIdentity` 提供基于 execution + workflow version + decision fingerprint + ordered node IDs 的确定性 Frontier key；
- `WorkflowFrontierStatus` 提供 `pending → claimed → running → completed/failed` 及 `retry_wait` 生命周期；terminal Frontier 不允许重新 claim；
- `WorkflowFrontier` 已建立 PostgreSQL 持久化模型，包含 tenant、execution、workflow version、decision fingerprint、frontier key、node IDs、attempt、Worker lease、available time、terminal/error facts；
- Alembic `0035_workflow_frontier` 已加入 migration chain，正式建立 `workflow_frontiers` 表及 tenant/key 唯一约束、claim/execution/lease 索引；
- `enqueue_frontier()` 使用 Frontier Identity + `uq_workflow_frontier_tenant_key` 完成幂等入队；并发唯一键冲突后读取既有 Frontier，不创建第二个 work item；该 Repository 只负责 INSERT/SELECT/flush，不负责 commit；
- `claim_next_frontier()` 使用 tenant scope + `FOR UPDATE SKIP LOCKED`，只负责 claim 与 flush，不负责 commit；Scheduler/Worker 保持 caller-owned transaction；
- `recover_expired_frontiers()` 锁定已过期 `claimed/running` Frontier，清除旧 Worker ownership 并回到 `retry_wait`，供下一次 Claim 重新分配；
- `transition_owned_frontier()` 强制同时校验 `worker_owner + attempt` fencing generation，stale Worker 不能覆盖新 Worker 的 Frontier；
- `renew_owned_frontier_lease()` 提供带 fencing generation 的 Frontier lease heartbeat；
- Scheduled Trigger 现在在同一调用方事务内为新 pending Execution 创建首个 Durable Frontier，Frontier 与 Execution 共享 tenant / workflow version / execution identity；
- 默认 `WorkflowWorker` 已切换为 `PlannerDrivenDurableFrontierWorkflowWorker`，Claim Frontier 后在同一事务取得对应 Execution ownership，再复用既有 `WorkflowRuntime` 的 Planner、Node execution 与 Checkpoint 能力；
- Frontier Worker 同时维护 Frontier lease heartbeat 与既有 Execution lease heartbeat，并在 Execution terminal state 后通过 fencing transition 收敛 Frontier terminal state；
- `FrontierRetryPolicy` 提供 max attempts、bounded exponential backoff；
- `schedule_frontier_retry()` 将当前 Worker 持有的 Frontier 转为 `retry_wait` 并设置 `available_at`，下一次 Claim 才递增 attempt；达到 max attempts 后同一 Frontier 转为 `failed`；
- Retry scheduling 不创建新的 WorkflowExecution / Frontier，并通过既有 fencing transition 防止 stale Worker 写入；
- `complete_frontier_with_checkpoint()` 固定 Frontier → Execution/Checkpoint → Next Frontier 的锁顺序，在同一外层事务内完成当前 Frontier terminal、Checkpoint sequence 分配及 Next Frontier 幂等入队基础能力；
- `PlannerDrivenDurableFrontierWorkflowWorker` 复用 `WorkflowRuntime._load_completed_resume_nodes()`、`_build_frontier_branch_states()`、`_execute_node_with_policy()`、`_execute_multi_frontier()` 与 `WorkflowDagResumePlanner`，每次 dispatch 只消费当前 Planner frontier；
- DAG 当前 frontier 成功后重新读取持久化 Node facts，重新运行唯一 Planner，并以新的 `decision_fingerprint + ordered node IDs` 生成 Next Frontier identity；
- 无 Edge 顺序 Workflow 每次只推进一个未完成 Node，按 Definition 顺序生成下一 Frontier；
- Frontier progression 不复制 DAG 条件求值、State Merge、Runtime 或 Retry 算法；
- Runtime 异常统一由 Planner-driven Worker 分类：HTTP 408 / 429 / 5xx、TimeoutError、ConnectionError、CircuitOpenError 进入 Frontier Retry；Planner/Contract/其他业务异常进入 Frontier Failed；
- Runtime 异常首先 rollback 当前事务，再在新事务中重新锁定 Frontier 与 Execution，Retry/Failed 与 Execution ownership 释放一起提交；retry exhausted 时同一 Frontier 与 Execution 同时进入 `failed`；
- Frontier Runtime failure convergence 不依赖 lease 过期作为正常 Retry 机制，expired lease recovery 仅负责 Worker 丢失 ownership 的异常恢复；
- Worker 成功路径已统一调用 `complete_frontier_with_checkpoint()`，由单一 progression primitive 负责 Frontier fencing transition、Checkpoint append 与 Next Frontier enqueue，Worker 不再分别操作这些持久化事实；
- 单 Node Frontier 将同一事务中的最新 `WorkflowNodeExecution` attempt/status/output 绑定到 Node-level Checkpoint；Multi-frontier 使用 merged state 创建 Execution-level Checkpoint；
- Progression contract 强制 Next Frontier 与当前 Execution / Workflow Version 一致，禁止 self-loop identity，并要求存在后继时 Execution 保持 running、无后继时 Execution 进入 completed；
- Automatic Recovery Scheduler 独立运行于 Scheduler Service 进程，不进入 API 多实例后台任务；扫描 failed Execution 后委托唯一 Recovery Domain Service；
- Automatic Recovery 只允许 failed、无 active Worker ownership 且存在合法 resumable Checkpoint 的 Execution；冷却时间与最大恢复次数由唯一 Recovery Policy 决定；
- Recovery Trace Link 校验 Source / Resume / Checkpoint tenant、workflow version 与 checkpoint sequence lineage；自动恢复路径使用 caller-owned transaction，Resume / Frontier / trace link 一次提交。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7 Conditional Branching
  └── Conditional Branching Closure     ✅ 当前实现范围
          ↓
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
  ├── Unified success persistence path  ✅
  ├── Durable Resume Bootstrap          ✅
  ├── Recovery Trace atomic transaction  ✅
  ├── Join predecessor contract         ✅
  ├── Resume tenant boundary            ✅
  └── Recovery Node Fact lineage guard  ✅ 本轮
          ↓
继续主线直到全部任务完成
```

下一主线：**Recovery / Replay Closure**，继续收敛 Resume Checkpoint sequence / Source checkpoint lineage、Recovery fencing generation、Replay identity、旧 Worker late-write 防护以及 Multi-frontier Join Recovery 的完整生命周期。

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Scheduler → Frontier → Worker → Runtime → Retry → Checkpoint → Next Frontier → Recovery 生命周期。