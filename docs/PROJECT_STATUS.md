# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭**。
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Contract、顺序 Runtime Resume、HTTP Resume API、Recovery Policy / Domain、Recovery Scan、Scheduler 生命周期、Recovery Event Contract、Recovery Outcome Contract、created / idempotency_hit 并发收敛及 DAG Branch State Merge Contract 已完成；Multi-frontier Resume Runtime、统一 observability 接入与自动恢复 Real API / Worker 仍在主线推进。**
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
Node transition / DAG frontier
              ↓
Checkpoint / Branch State Merge
```

职责冻结：**Scheduler 负责什么时候检查/触发；Recovery Policy 负责是否允许自动恢复；Recovery Domain 负责如何安全创建 Resume；Resume Outcome Contract 负责 created / idempotency_hit 事实；Recovery Event Contract 负责统一恢复控制面事件；DAG State Merge Contract 负责多 frontier 分支状态的安全收敛；Worker 负责执行；WorkflowExecutionService 负责状态机与 Resume 安全边界；WorkflowRuntime 负责节点/frontier；Checkpoint 记录执行事实。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `0033_workflow_execution_resume_contract`；
- `0034_terminal_execution_releases_worker_lease`；
- Checkpoint immutable snapshot + transaction boundary；
- Resume Candidate / deterministic idempotency / lineage；
- Resume Planner / DAG Contract / frontier planner / Runtime sequence planner；
- Worker Resume Source / Checkpoint / Version revalidation；
- 第一版 DAG Runtime 只允许单一 frontier；
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
- State Merge 通过 Recovery package 正式入口暴露；
- 事件禁止写入 Checkpoint `state_data`、Secret、Provider credential 和完整业务 payload；
- Scheduler / Domain 不创建平行 Recovery metrics / trace 规则；
- Unit tests 已覆盖 Recovery Policy、Automatic Recovery、Resume Outcome Contract、Scheduler Outcome Convergence、Observability Event Contract 与 DAG State Merge Contract。

## DAG Branch State Merge Contract

```text
Completed Branch A ──┐
                     │
Completed Branch B ──┼──→ Branch State Merge
                     │          │
Completed Branch N ──┘          ↓
                         deterministic state_data
                                  │
                                  ├── same key + same value → merge
                                  │
                                  └── same key + different value → reject
```

Merge Contract 当前是安全边界，不等价于完整 DAG Join 语义：

1. Branch Node ID 必须唯一且非空；
2. 每个 Branch `state_data` 必须为对象；
3. 状态键必须为非空字符串；
4. 相同键相同值允许合并；
5. 相同键不同值必须拒绝；
6. Merge 不采用 last-write-wins；
7. Merge 返回独立深拷贝，禁止调用方修改输入 Checkpoint 快照；
8. 多 frontier Runtime 仍未接入该 Contract，避免在 Planner/Runtime 尚未完成前宣称已经支持并行 Resume。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test** 作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填通过。

## 下一步主线

1. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；若当前没有统一基础设施，继续保持领域事件出口，不新增平行 exporter；
2. 将 DAG State Merge Contract 接入 Multi-frontier Resume Planner；
3. 扩展 DAG Runtime 从单 frontier 到多 frontier，并明确 branch execution / join 边界；
4. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口，但不作为当前主线阻塞项；
5. 完成 Phase 2.6 Closure；
6. 进入下一阶段企业级执行能力。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。