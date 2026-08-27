# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Contract、HTTP Resume API、Recovery Policy / Domain、Recovery Scan、Scheduler 生命周期、Recovery Event Contract、Recovery Outcome Contract、created / idempotency_hit 并发收敛、DAG Branch State Merge Contract、Multi-frontier Runtime Plan、Multi-frontier Branch Execution Coordinator、Branch Checkpoint Boundary、真实 WorkflowRuntime Multi-frontier Resume、Join readiness / execution / idempotency / checkpoint、统一 Recovery Telemetry Facade、Automatic Recovery Trace 生命周期、Recovery → Resume Trace Link、Worker / Runtime Trace Continuity、Scheduler Trace Context 与 Scheduler Runtime Trace Integration 已完成；当前主线进入 Scheduler → Recovery parent/child trace lineage、Worker claim / lease / fencing 持久化闭环与 Phase 2.6 Closure。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 当前执行架构

```text
API / Trigger
    ↓
Scheduler Service
    ├── ScheduledTriggerScheduler
    └── WorkflowRecoveryScheduler
              │
              │ Scheduler trace = S
              ↓
       Recovery Policy / Domain
              │
              │ child recovery trace = R
              │ parent_trace_id = S
              ↓
       WorkflowRecoveryTelemetry
              ↓
       Resume Outcome Contract
          ├── created
          └── idempotency_hit
              ↓
       persistent Recovery Trace Link
              ↓
       pending Resume Execution
              ↓
Worker claim + lease + fencing
              ↓
WorkflowExecutionService
              ↓
WorkflowRuntime
              ↓
DAG Resume Planner
              ↓
Multi-frontier Runtime Plan
          ┌───┴───┐
          ↓       ↓
       Branch A Branch B
          │       │
          └───┬───┘
              ↓
       NodeExecution + Checkpoint
              ↓
       Branch State Merge
              ↓
          Join Ready
              ↓
       Join NodeExecution
              ↓
       Join Checkpoint
              ↓
       recompute next frontier
              ↓
          next Branch / Join
```

职责冻结：**Scheduler 负责什么时候检查/触发；Recovery Policy 负责是否允许自动恢复；Recovery Domain 负责如何安全创建 Resume；Resume Outcome Contract 负责 created / idempotency_hit 事实；Recovery Event / Telemetry Contract 负责统一恢复控制面事件与 Trace/Metrics 出口；Scheduler Trace Contract 负责 Scan trace 生命周期并通过 `parent_trace_id` 关联 Automatic Recovery child trace；DAG State Merge Contract 负责多 frontier 分支状态的安全收敛；Multi-frontier Runtime Planner 负责将 frontier + 已验证分支状态转换为确定性 Runtime Plan；Multi-frontier Branch Executor 负责在单 Worker 内以确定性顺序执行 Branch、隔离 Branch state 并判定 Join readiness；Join Executor 负责纯状态汇聚；Worker 负责 ownership / lease / fencing；WorkflowExecutionService 负责状态机与持久化事务边界；WorkflowRuntime 负责实际 Node 执行、Resume frontier 重新规划与 Retry；Checkpoint 记录执行事实。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `0033_workflow_execution_resume_contract`；
- `0034_terminal_execution_releases_worker_lease`；
- Checkpoint immutable snapshot + transaction boundary；
- Resume Candidate / deterministic idempotency / lineage；
- Resume Planner / DAG Contract / frontier planner；
- Worker Resume Source / Checkpoint / Version revalidation；
- HTTP Resume API：`POST /api/v1/workflows/executions/{execution_id}/resume`；
- `WorkflowExecutionRecoveryPolicy`：默认 `max_attempts=3`、`cooldown_seconds=60`；
- `WorkflowExecutionAutomaticRecoveryService`；
- `WorkflowRecoveryScheduler.scan_once()` / `run_forever()`；
- Scheduler Service 接入 Recovery Scan 独立生命周期；
- Recovery Scan 聚合 `candidates / eligible / recovered / rejected / contention / failed`；
- `WorkflowRecoveryEvent` / `WorkflowRecoveryEventLogger` 正式 Recovery observability 事件出口；
- `WorkflowRecoveryTelemetry` 统一 Logger / Trace / Metrics fan-out；
- `workflow.recovery.attempt` / `workflow.recovery.scan.completed` / trace lifecycle events；
- Automatic Recovery `recover()` 已接入 `WorkflowRecoveryTelemetry.start_trace()` / `finish_trace()`，attempt event 与 trace 使用同一 `trace_id`；
- `WorkflowExecutionResumeOutcome` 正式区分 `created` / `idempotency_hit`；
- `WorkflowExecutionResumeContractService`：Source Execution row lock + deterministic key precheck + 既有 Resume Domain delegation；
- Automatic Recovery 事件携带 `outcome`；
- Scheduler 精确统计 `created / idempotency_hit / contention`；
- Scheduler 不再重复发射 Recovery Attempt 事件；
- `WorkflowDagBranchStateMergeService` 正式冻结多 frontier 分支状态 Merge Contract；
- 相同顶层状态键只有在所有分支值相等时才合并；
- 不同分支对同一顶层状态键写入不同值时显式拒绝，不允许 last-write-wins 隐式覆盖；
- Merge 仅处理顶层状态键，不自动解释嵌套对象、列表追加或业务语义冲突；
- `WorkflowDagResumeRuntimePlanner` 已接入 Branch State Merge Contract；
- 单 frontier 继续兼容既有 `state_data` 调用；
- 多 frontier 必须显式提供每个 frontier Node 对应的 branch state；
- Runtime Plan 返回确定性 `frontier_node_ids` / `nodes` / merged `state_data`；
- 多 frontier 不再被 Runtime Planner 直接拒绝，也不允许通过属性访问隐式选择单一 Node；
- `WorkflowDagMultiFrontierExecutor` 已建立 Branch execution coordination boundary：每个 Branch 使用独立 state 深拷贝、按确定性 frontier 顺序执行、Branch 失败立即阻止后续 Branch、全部 Branch 成功后才允许 State Merge 与 `join_ready=True`；
- 真实 `WorkflowRuntime` 已接入 `WorkflowDagMultiFrontierExecutor`；
- Resume Runtime 不再使用旧的单 Node Sequence Planner 作为真实执行入口；
- 每一轮 Resume 都从 Source Execution + 当前 Resume Execution 的已持久化 `WorkflowNodeExecution` 完成事实重新计算 frontier；
- frontier Branch state 从已完成 predecessor 的 `output_data` 重建；多个 predecessor 必须通过正式 State Merge Contract 合并，禁止共享 Resume Execution 单一 state；
- Branch Node 通过现有 `WorkflowExecutionService.transition_node()` 完成 Worker ownership / fencing、Node Execution 与 Checkpoint 同事务持久化；
- 当前 Multi-frontier 在单 Worker 内确定性顺序执行，不伪装成多 Worker 并行；
- 一个 frontier 完成后重新读取持久化完成事实并计算下一 frontier，避免一次性展平 DAG；
- 如果下一 frontier 仍为多个 Node，则继续进入 Multi-frontier Executor；如果只有一个 Node，则复用同一 Node Retry / Checkpoint Contract；
- Join Readiness 要求所有 predecessor completed，并从持久化 predecessor `output_data` 构造 Join state；
- Join State Merge 继续禁止 last-write-wins；
- Join Node 是纯 state aggregation，不调用 Model Provider；
- Join Node 使用现有 `(execution_id, node_id)` NodeExecution 唯一事实与 Worker ownership / fencing 保证幂等；
- Join NodeExecution / Checkpoint 继续复用 `WorkflowExecutionService.transition_node()`，未新增 Join 专用数据库表；
- Join completed 后重新读取持久化 completed facts，再由 DAG Planner 计算 downstream frontier；
- `WorkflowRecoveryTelemetry` 不携带 Checkpoint `state_data`、Secret、Provider credential 或完整业务 payload；
- Automatic Recovery telemetry 使用 `phase=automatic_recovery`，并记录 attempt / trace start / trace finish 的统一关联字段；
- `WorkflowRecoveryEvent` 新增 `parent_trace_id`，用于 Scheduler parent trace → Automatic Recovery child trace 的控制面 lineage；
- `WorkflowRecoveryScheduler.scan_once()` 为每轮 Scan 创建 parent trace，并将其传递给每个 Automatic Recovery；
- Automatic Recovery child trace 保持独立 `trace_id`，避免一个 Scheduler Scan trace 被多个 Recovery 生命周期重复 finish；
- Worker / Runtime 继续从持久化 Recovery Trace Link 恢复 child `trace_id`；
- 新增 / 更新 Scheduler Recovery 与 Observability Unit Test 覆盖 parent trace 传播和字段序列化；

## Recovery Trace Lineage Contract

```text
WorkflowRecoveryScheduler.scan_once()
          │
          │ parent trace S
          ▼
WorkflowExecutionAutomaticRecoveryService.recover()
          │
          │ child trace R
          │ parent_trace_id = S
          ▼
Resume Execution
          │
          ▼
WorkflowRecoveryTraceLinkService
          │
          │ durable trace_id = R
          ▼
Worker claim
          │
          ▼
WorkflowRuntime
```

Contract 规则：

1. Scheduler Scan 使用独立 parent `trace_id`；
2. 每个 Automatic Recovery 使用独立 child `trace_id`；
3. Automatic Recovery 的 trace lifecycle 不得复用 Scheduler Scan 的 finish；
4. `parent_trace_id` 仅用于控制面 lineage，不写入业务 `input_data`；
5. Resume Execution 的 durable Trace Link 保存 child `trace_id`，Worker / Runtime 以此恢复 Recovery trace；
6. Trace 字段不得携带 Checkpoint `state_data`、Prompt、Secret、Provider credential 或完整业务 payload。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test 实际执行结果**作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填通过。

## 下一步主线

1. 完成 Worker claim / lease / fencing 与 Recovery Resume 的最终持久化闭环，重点验证 stale worker、lease loss、ownership fencing 不会错误完成 Recovery Execution；
2. 让 durable Recovery Trace Link 与 Worker lease 生命周期形成一致的控制面事实；
3. 完成 Real API + PostgreSQL + 独立 Worker 验证入口，但不作为当前主线阻塞项；
4. 完成 Phase 2.6 Closure；
5. Closure 后进入下一阶段企业级执行能力。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。
