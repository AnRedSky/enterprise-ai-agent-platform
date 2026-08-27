# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Contract、顺序 Runtime Resume、HTTP Resume API、Recovery Policy / Domain、Recovery Scan、Scheduler 生命周期与 Recovery Event Contract 已完成基础实现；自动恢复 Real API / Worker、统一 observability 接入、contention 收敛及 DAG 分支 Resume 仍在主线推进。**
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
       pending Resume Execution
              ↓
Worker claim + lease + fencing
              ↓
WorkflowExecutionService
              ↓
WorkflowRuntime
              ↓
Node transition
              ↓
Checkpoint / terminal lease release
```

职责冻结：**Scheduler 负责什么时候检查/触发；Recovery Policy 负责是否允许自动恢复；Recovery Domain 负责如何安全创建 Resume；Worker 负责执行；WorkflowExecutionService 负责状态机与 Resume 安全边界；WorkflowRuntime 负责节点/frontier；Checkpoint 记录执行事实。**

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
- 事件禁止写入 Checkpoint `state_data`、Secret、Provider credential 和完整业务 payload；
- Scheduler / Domain 不创建平行 Recovery metrics / trace 规则；
- Unit tests 覆盖 Recovery Policy、Automatic Recovery、Scheduler Scan 与 Observability Event Contract。

## Recovery Observability Contract

```text
Recovery Domain
    ↓
workflow.recovery.attempt
    ↓
Scheduler Scan aggregate
    ↓
workflow.recovery.scan.completed
    ↓
未来统一 Metrics / Trace
```

统一字段：

```text
execution_id
resume_execution_id
reason_code
attempt_count
max_attempts
candidates
eligible
recovered
rejected
contention
failed
scan_limit
occurred_at
```

当前 `contention` 只是稳定聚合维度；在能够可靠识别 row-lock / idempotency contention 前，Scheduler 不根据异常类型猜测竞争类型。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test + API Test** 作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate 暂不作为主线阻塞条件。真实 API 测试必须使用真实 HTTP + PostgreSQL；后台服务生命周期由开发者人工控制。

测试结果只能记录实际执行结果，不得预填通过。

## 下一步主线

1. 增加自动恢复 Real HTTP + PostgreSQL + 独立 Worker 测试入口；
2. 将 Recovery Event Contract 接入项目已有统一 observability / trace 基础设施；
3. 精确实现 recovery contention / idempotency convergence；
4. 冻结 DAG Branch State Merge Contract；
5. 实现 Multi-frontier Resume；
6. 完成 Phase 2.6 Closure；
7. 进入下一阶段企业级执行能力。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。