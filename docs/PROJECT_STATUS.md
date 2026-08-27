# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前 `main` HEAD：继续推进 Phase 2.7 Advanced Workflow Orchestration，主线已从 Conditional Branching Closure 转入 Durable Frontier Scheduling。
- 本轮已完成：**Scheduler → Durable Frontier → Worker 实际桥接**；Scheduled Trigger 创建 pending Execution 时同步创建首个 Durable Frontier，默认 Worker 以 Frontier 为调度入口并复用唯一 WorkflowExecution Runtime。
- Runtime Durable Commit Ownership：**已完成；Runtime NodeExecution / Checkpoint transition 使用 `commit=False`，由外层 Execution `completed/failed` transition 统一提交；直接调用方默认保持 `commit=True` 兼容。**
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**已完成既定实现范围，不作为当前主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**继续按最新治理规则推进，不作为当前主线阻塞条件。**
- Frontend Phase 1.3：**SSE / Runtime 公共边界、Runtime Execution 页面、Chat streaming 消费、Chat / Runtime 失败、断流、取消 UI 生命周期均已完成。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching Closure 已完成其当前实现范围，Durable Frontier 已完成持久化、Claim/Fencing/Recovery，并已接入 Scheduled Trigger 与默认 Worker。**

## Phase 2.7 当前实现

- `WorkflowConditionEvaluator` 是唯一条件求值入口；
- DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- 已实现深度 / 节点数上限；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default 数量、重复 edge、未知 Node 和循环图；当前第一版 DAG Contract 要求单 root；
- Conditional frontier 按 Definition 顺序确定性选择并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts，Join readiness 不复制条件解析；
- 首次执行与 Resume 均通过统一 DAG Planner；
- Conditional Join 只消费 Planner selected predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`；
- Resume Contract 在 Source Execution row lock 后再次强制使用 `locked_execution.tenant_id` 查询最新 Checkpoint；
- Runtime 持久化 `workflow.dag.frontier_decided` decision metadata；
- Planner 生成 deterministic `decision_fingerprint`，同时绑定 completed Node facts、条件 source state、frontier 与 selected predecessor；
- Runtime Plan 显式携带 Planner fingerprint，Runtime 不再复制 Decision identity 计算逻辑；
- Decision Trace 不保存业务 state_data，只保存 fingerprint 和可审计的节点选择 metadata，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state / `join_ready=true`；
- 同一 Recovery trace 下相同 durable completed facts 必须保持相同 `decision_fingerprint`，Replay Guard 对不一致 Decision 立即失败；
- DAG Decision Trace 使用 execution + tenant + workflow version + trace + decision fingerprint 作为幂等 identity；
- Checkpoint 自动序号分配锁定目标 `WorkflowExecution` 后读取最大 sequence；
- Checkpoint Node fact completeness、Recovery Trace lineage、Decision rebuild、Trace lineage continuity、payload drift guard、fingerprint JSON boundary、single DAG planning boundary、tenant boundary、Resume idempotency lineage/key determinism、SAVEPOINT、Recovery Commit Ownership 与 Runtime Durable Commit Ownership 均已完成；
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
- 默认 `WorkflowWorker` 已切换为 `DurableFrontierWorkflowWorker`，Claim Frontier 后在同一事务取得对应 Execution ownership，再复用既有 `LeaseAwareWorkflowWorker` / `WorkflowExecutionService` Runtime；
- Frontier Worker 同时维护 Frontier lease heartbeat 与既有 Execution lease heartbeat，并在 Execution terminal state 后通过 `transition_owned_frontier()` 收敛 Frontier terminal state；
- Frontier lease recovery / fencing repository 不负责 commit，由 Scheduler/Worker caller 统一提交。

## 当前开发策略

暂停完整测试流程，只以 Unit Test 实际执行结果作为当前开发验证范围。Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 暂不阻塞主线。不得把未执行测试写成通过。

## 最新执行限制

当前环境只能通过 GitHub Repository API 直接核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm；因此本轮继续不伪造 Unit Test 结果。

## 当前主线

```text
Phase 2.7 Conditional Branching
  ├── Evaluator                         ✅
  ├── DAG Contract                     ✅
  ├── Conditional Planner              ✅
  ├── Initial Execution Runtime        ✅
  ├── Resume Runtime Integration       ✅
  ├── Conditional Join                 ✅
  ├── Durable tenant boundary          ✅
  ├── Checkpoint tenant boundary       ✅
  ├── Conditional Decision Trace       ✅
  ├── Resume Contract tenant scope     ✅
  ├── Branch Checkpoint Gate            ✅
  ├── Decision Fingerprint              ✅
  ├── Runtime Plan fingerprint          ✅
  ├── Recovery Frontier Replay Guard    ✅
  ├── Decision Trace Idempotency        ✅
  ├── Checkpoint sequence serialization ✅
  ├── Checkpoint fact completeness      ✅
  ├── Recovery Trace Checkpoint Lineage ✅
  ├── Conditional Decision Rebuild      ✅
  ├── Trace Lineage 连续性              ✅
  ├── Decision Trace payload drift guard ✅
  ├── Deterministic fingerprint JSON boundary ✅
  ├── Single DAG Decision Planning Boundary ✅
  ├── Checkpoint Durable Write Tenant Boundary ✅
  ├── Resume Idempotency Lineage Drift Guard ✅
  ├── Resume Idempotency Key Determinism Guard ✅
  ├── Resume Transaction Savepoint Boundary ✅
  ├── Recovery Commit Ownership Boundary ✅
  ├── Runtime Durable Commit Ownership  ✅
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
  ├── Scheduler → Frontier enqueue     ✅ 本轮
  ├── Frontier → Worker claim           ✅ 本轮
  ├── Worker → Runtime bridge           ✅ 本轮
  ├── Frontier lease heartbeat           ✅ 本轮
  ├── Retry scheduling                  ⏭
  └── Frontier → Checkpoint progression ⏭
          ↓
继续主线直到全部任务完成
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Scheduler → Frontier → Worker → Runtime。