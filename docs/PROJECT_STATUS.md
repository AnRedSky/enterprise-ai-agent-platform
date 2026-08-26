# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Execution Contract、第一版顺序 Runtime Resume、HTTP Resume API、自动恢复 Policy / Domain Service、Recovery Scan 与 Scheduler Service 生命周期接入已完成基础实现；Recovery observability、自动恢复 Real API / Worker 验收与 DAG 分支 Resume 仍在主线推进。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 当前产品级执行架构

```text
API Service
   ↓
Trigger Domain
   ↓
Scheduler Service
   ├── ScheduledTriggerScheduler
   │      ↓
   │  PostgreSQL pending WorkflowExecution
   │
   └── WorkflowRecoveryScheduler
          ↓
       Recovery Policy / Domain
          ↓
       PostgreSQL pending Resume Execution
          ↓
Worker claim + lease + ownership fencing
   ↓
WorkflowExecutionService
   ↓
WorkflowRuntime
   ↓
Node transition
   ↓
Checkpoint append / terminal lease release
```

核心职责：**Scheduler 负责“什么时候检查/触发”，Recovery Policy 负责“是否允许自动恢复”，Recovery Domain 负责“如何安全创建 Resume”，Worker 负责“执行什么”，WorkflowExecutionService 负责状态机与 Resume 安全边界，WorkflowRuntime 负责节点执行与 frontier，Checkpoint 负责执行事实。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `0033_workflow_execution_resume_contract`；
- `0034_terminal_execution_releases_worker_lease`；
- Checkpoint immutable snapshot + transaction boundary；
- `WorkflowExecutionCheckpointRecoveryService`；
- `WorkflowExecutionService.resume_from_latest_checkpoint()`；
- Resume deterministic idempotency + lineage；
- Source failed Execution 不被复活；
- Resume Planner / DAG Contract / Frontier Planner / Runtime Sequence Planner；
- Worker Resume 前重新校验 Source / Checkpoint / Version；
- 第一版 DAG Runtime 只允许单一 frontier；
- HTTP Resume API：`POST /api/v1/workflows/executions/{execution_id}/resume`；
- Execution response 增加 `resume_of_execution_id + resume_checkpoint_sequence`；
- `WorkflowExecutionRecoveryPolicy`：默认 `max_attempts=3`、`cooldown_seconds=60`；
- `WorkflowExecutionRecoveryPolicyEvaluator`：纯规则、无数据库副作用；
- `WorkflowExecutionAutomaticRecoveryService`：Policy + Candidate + lineage + Resume Contract；
- `WorkflowRecoveryScheduler.scan_once()`：Scheduler 侧 Recovery Scan；
- `WorkflowRecoveryScheduler.run_forever()`：独立 Recovery Scan 生命周期；
- `backend/app/entrypoints/scheduler.py`：Scheduled Trigger 与 Recovery Scan 同进程双循环、独立 Session、独立异常边界；
- Recovery Scan 聚合 `candidates / eligible / recovered / rejected / contention / failed`；
- `tests/unit/test_workflow_recovery_policy.py`；
- `tests/unit/test_workflow_automatic_recovery_service.py`；
- `tests/unit/test_workflow_recovery_scheduler.py`；
- 原有 Durable Resume Real API / Worker / DAG / failure-boundary 验收入口继续保留，但当前不作为主线阻塞项。

## Durable Recovery Policy Contract

```text
failed Execution
      ↓
worker ownership? ── yes → reject
      ↓ no
valid Checkpoint? ── no → reject
      ↓ yes
max attempts? ── reached → reject
      ↓ no
cooldown? ── active → reject + retry_after
      ↓ elapsed
Recovery Domain
      ↓
pending Resume Execution
      ↓
Worker normal claim
```

规则：

1. 仅自动恢复 `failed` Execution；不直接恢复 `running`。
2. `worker_owner != NULL` 时拒绝自动恢复。
3. Checkpoint 必须满足既定 `node.completed + execution.running` 恢复边界。
4. 默认最多 3 次 Resume lineage 尝试。
5. Source failed 后默认冷却 60 秒。
6. `max_attempts=0` 关闭自动恢复，但不影响人工 Resume API。
7. Resume 次数沿 `resume_of_execution_id` lineage 计算，与普通 Retry 分离。
8. Recovery Policy 不产生数据库副作用。
9. Recovery Domain 不直接启动 Runtime；Resume 仍进入 Worker claim。
10. deterministic idempotency key + DB unique constraint 作为最终幂等兜底。

## Scheduler Recovery Scan Contract

```text
Scheduler Service
    ├── Scheduled Trigger loop
    │
    └── Recovery Scan loop
           ↓
        failed + worker_owner IS NULL
           ↓
        Recovery Domain evaluate/recover
           ↓
        pending Resume Execution
           ↓
        Worker claim
```

Scheduler 不复制 Recovery Policy、不直接修改 failed 状态、不直接抢 Worker ownership、不直接启动 Runtime。

多个 Scheduler 实例可以同时扫描同一 Execution，Source row lock + deterministic idempotency + DB unique constraint 负责最终收敛。

## 当前开发策略

按当前要求暂停完整测试流程，不把 Backend Regression、Frontend Gate、Browser E2E、Real API Acceptance 或服务重启作为当前主线开发门槛。当前开发阶段只保留新增 / 修改代码的单元测试作为验证目标，并继续推进主线实现。

真实联调脚本仍保持可重复执行，但服务生命周期必须由开发者人工控制。

## 本轮测试状态

本轮新增测试源码已经提交，但当前执行环境无法直接访问仓库运行本地 `uv run pytest`，因此**不得虚构新增测试通过结果**。上一轮开发者实际反馈的稳定基线仍为：

```text
DAG / Resume targeted unit tests
42 passed in 1.26s

uv run pytest -q
468 passed, 3 skipped, 40 deselected in 31.23s

05_run_durable_resume_real_tests.ps1
success real_api: 1 passed in 4.19s
full linear DAG Resume real_api: 1 passed in 4.36s
failure-boundary real_api: 1 passed in 2.13s
```

## 下一步主线

1. Recovery Scan counters 接入 Scheduler observability / trace；
2. 增加自动恢复 Real API + PostgreSQL + 独立 Worker 验收入口，但不作为当前主线阻塞项；
3. 验证 Scheduled Trigger Dispatch 与 Recovery Scan 的并发 / Session / failure isolation；
4. 自动恢复稳定后冻结 DAG 分支状态合并 Contract；
5. 实现多 frontier Resume；
6. 完成 Phase 2.6 后进入下一阶段主线能力。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract、Recovery Policy、Automatic Recovery Domain、Recovery Scheduler、Resume Planner、Worker Resume Runtime 与 HTTP Resume API 都属于 API / Worker / Scheduler 进程内代码变更。代码更新后必须由开发者人工重启受影响服务；Real API / Backend Gate 不负责启动、停止或重启服务。
