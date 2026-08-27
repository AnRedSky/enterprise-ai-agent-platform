# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭**。
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Contract、HTTP Resume API、Recovery Policy / Domain、Recovery Scan、Scheduler 生命周期、Recovery Event Contract、Recovery Outcome Contract、created / idempotency_hit 并发收敛、DAG Branch State Merge Contract、Multi-frontier Runtime Plan、Multi-frontier Branch Execution Coordinator、Branch Checkpoint Boundary 与真实 WorkflowRuntime Multi-frontier Resume 接入已完成；当前主线进入 Join readiness / next frontier 持久化事实闭环，统一 observability 接入与自动恢复 Real API / Worker 仍在主线推进。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 当前执行架构

```text
API / Trigger
    ↓
Scheduler Service
    ├── ScheduledTriggerScheduler
    └── WorkflowRecoveryScheduler
              ↓
       Recovery Policy / Domain
              ↓
       Resume Outcome Contract
          ├── created
          └── idempotency_hit
              ↓
       workflow.recovery.attempt
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
       transition_node()
              ↓
 NodeExecution + Checkpoint（同事务）
              ↓
       Branch State Merge
              ↓
          Join Ready
              ↓
       recompute next frontier
              ↓
          next Branch / Join
```

职责冻结：**Scheduler 负责什么时候检查/触发；Recovery Policy 负责是否允许自动恢复；Recovery Domain 负责如何安全创建 Resume；Resume Outcome Contract 负责 created / idempotency_hit 事实；Recovery Event Contract 负责统一恢复控制面事件；DAG State Merge Contract 负责多 frontier 分支状态的安全收敛；Multi-frontier Runtime Planner 负责将 frontier + 已验证分支状态转换为确定性 Runtime Plan；Multi-frontier Branch Executor 负责在单 Worker 内以确定性顺序执行 Branch、隔离 Branch state 并判定 Join readiness；Worker 负责 ownership / lease / fencing；WorkflowExecutionService 负责状态机与持久化事务边界；WorkflowRuntime 负责实际 Node 执行、Resume frontier 重新规划与 Retry；Checkpoint 记录执行事实。**

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
- `workflow.recovery.attempt`；
- `workflow.recovery.scan.completed`；
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
- `backend/tests/unit/test_workflow_runtime.py` 新增 Branch state reconstruction / Join predecessor merge Unit Test；
- 已记录 Runtime Plan Contract 漂移工程错误：`docs/04-errors/2026-08-27-phase-2-6-runtime-plan-contract-drift.md`；
- Recovery Event 禁止写入 Checkpoint `state_data`、Secret、Provider credential 和完整业务 payload；
- Scheduler / Domain 不创建平行 Recovery metrics / trace 规则。

## DAG Multi-frontier Runtime Contract

```text
Source Execution + Resume Execution completed Node facts
                    ↓
          WorkflowDagResumePlanner
                    ↓
             frontier = [A, B]
                    ↓
    predecessor output_data reconstruction
                    ↓
        WorkflowDagStateMergeContract
                    ↓
       WorkflowDagResumeRuntimePlan
                    ↓
     WorkflowDagMultiFrontierExecutor
              ┌─────┴─────┐
              ↓           ↓
           Branch A    Branch B
              │           │
              ↓           ↓
       transition_node()  transition_node()
              │           │
              ↓           ↓
        NodeExecution + Checkpoint
              └─────┬─────┘
                    ↓
              Join readiness
                    ↓
          persisted completed facts
                    ↓
        recompute next frontier
```

Contract 规则：

1. frontier Node ID 唯一、确定性排序；
2. 多 frontier 不允许缺少任一分支状态；
3. 不允许提供非 frontier 的额外分支状态；
4. Branch State Merge 禁止 last-write-wins；
5. Merge Result 为独立深拷贝；
6. 单 frontier 保持原有 `state_data` API 兼容；
7. 多 frontier 不再在 Runtime 层伪装成单 Node；
8. `frontier_node_id` / `node` 只为单 frontier 提供兼容访问，多 frontier 显式拒绝隐式选择；
9. Branch Executor 当前采用**单 Worker 内确定性顺序执行**，不虚构多 Worker 并行；
10. 任一 Branch 执行或 Checkpoint 失败，Join 不得就绪，异常向上层 Worker / ExecutionService 传播；
11. 所有 Branch 成功且 Checkpoint 已由 `transition_node()` 持久化后才允许生成 merged state 与 `join_ready=True`；
12. Executor 不直接修改 ORM / DB，Node 状态与 Checkpoint 必须通过 `WorkflowExecutionService.transition_node()`；
13. 当前已完成真实 WorkflowRuntime Resume 接入，但尚未完成独立 Join Node 状态机 / next frontier 持久化 Contract 的最终 Closure。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test 实际执行结果**作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填通过。

## 下一步主线

1. 将 Join readiness 从 Runtime 内存事实提升为明确的持久化 / 状态机 Contract，避免“所有 Branch 完成”与“Join Node 已执行”混淆；
2. 完成 Join Node 的 NodeExecution / Checkpoint 事务边界，并验证 Join predecessor completion 的幂等性；
3. 完成 Join 后 next frontier 的正式 Runtime Contract，确保 Resume 在 Join 后继续恢复而不是重复执行 Branch；
4. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，保持领域事件出口，不新增平行 exporter；
5. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口，但不作为当前主线阻塞项；
6. 完成 Phase 2.6 Closure；
7. 进入下一阶段企业级执行能力。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。