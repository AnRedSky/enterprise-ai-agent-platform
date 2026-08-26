# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`，本轮开发基线从 `86284e873f7a8df16ce57bbea1ed53d423edbfdf` 开始。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Execution Contract、第一版顺序 Runtime Resume、HTTP Resume API、自动恢复 Policy / Domain Service 与 Scheduler Recovery Scan 已完成基础实现；Recovery Scan 接入 Scheduler 主循环与 DAG 分支 Resume 仍在主线推进。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前 main 已完成 Durable Resume HTTP Contract：客户端通过 `POST /api/v1/workflows/executions/{execution_id}/resume` 请求恢复，API 只执行 tenant / actor 权限校验并调用正式 `WorkflowExecutionService.resume_from_latest_checkpoint()`；恢复来源仍由 Checkpoint / Resume Candidate Domain 决定，Source failed Execution 不被复活，Resume Execution 仍以 pending 进入标准 Worker claim 路径。Execution API 响应暴露 `resume_of_execution_id + resume_checkpoint_sequence`，用于客户端 lineage 追踪。

最新 main 已新增 `0034_terminal_execution_releases_worker_lease`：Workflow Execution 进入 `completed` / `failed` / `cancelled` 终态时，由 PostgreSQL trigger 在同一次 status UPDATE 中原子清理 `worker_owner` 与 `worker_lease_expires_at`，避免终态提交与 ownership 释放之间出现可竞争窗口。

## 当前产品级执行架构

```text
API Service
   ↓
Trigger Domain
   ↓
Scheduler Service
   ├── Scheduled Trigger Slot Dispatch
   │      ↓
   │  PostgreSQL pending WorkflowExecution
   │
   └── Recovery Scan
          ↓
       Recovery Policy / Domain
          ↓
       PostgreSQL pending Resume Execution
          ↓
Worker claim + lease + ownership fencing
   ↓
Recovery Boundary
   ↓
Lease Heartbeat
   ↓
WorkflowExecutionService
   ├── Normal Execution
   │      ↓
   │  WorkflowRuntime
   │      ↓
   │  Node transition
   │      ↓
   │  Checkpoint append
   │
   └── Resume Execution
          ↓
       Source / Checkpoint revalidation
          ↓
       Checkpoint state_data
          ↓
       完整 DAG Definition
          ↓
       DAG Contract / Frontier Planner
          ↓
       WorkflowRuntime 单一 frontier
          ↓
       后续 Node transition
          ↓
       新 Checkpoint append / terminal lease release
```

核心职责冻结：**Scheduler 负责“什么时候检查/触发”，Recovery Policy 负责“什么 Execution 可以自动恢复、何时恢复、最多恢复多少次”，Recovery Domain Service 负责将策略与 Resume Contract 串联，Worker 负责“执行什么”，WorkflowExecutionService 负责执行状态机与 Resume 安全边界，WorkflowRuntime 负责“如何执行节点”和当前 DAG Resume frontier 选择，Checkpoint 负责“记录已完成执行事实”，Resume Candidate assessment 负责“判断是否满足恢复前置条件”，Resume Execution contract 负责“创建新的 pending 恢复任务并固定来源事实”，HTTP Resume API 负责“提供受权限保护的人工恢复入口”。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `0033_workflow_execution_resume_contract`；
- `0034_terminal_execution_releases_worker_lease`；
- `WorkflowExecutionCheckpoint` 不可变快照模型；
- `WorkflowExecutionCheckpointService.append()` / `append_next_in_transaction()` / `latest()`；
- `Node completed` 自动生成 Checkpoint；
- Node 状态与 Checkpoint 同事务提交；
- `execution_id + sequence` 数据库唯一约束；
- `WorkflowExecutionCheckpointRecoveryService`：只读 Resume Candidate 评估；
- `WorkflowExecutionService.resume_from_latest_checkpoint()`：创建新的 pending Resume Execution；
- Resume Execution 固定原 `workflow_version_id`；
- Resume Execution 持久化 `resume_of_execution_id + resume_checkpoint_sequence`；
- Resume Execution 使用 `resume:<execution_id>:checkpoint:<sequence>` 确定性幂等键；
- Source Execution 保持 `failed`；
- `WorkflowExecutionResumePlanner`：纯内存计算 Checkpoint 后续顺序 nodes；
- DAG Resume Contract / Frontier Planner / Runtime Planner / Linear Sequence Planner；
- DAG Resume Planner 第一版只接受单一 root；
- DAG Resume Planner 拒绝 predecessor 尚未完成的非闭包完成事实；
- Worker Resume 前重新校验 Source / Checkpoint / Version；
- Worker 使用 Checkpoint `state_data` 作为 Resume Execution Runtime 输入；
- 第一版 DAG Runtime 只允许单一 frontier，分支状态合并 Contract 未冻结前拒绝多个 frontier；
- 终态 Execution 的 Worker lease 由 PostgreSQL trigger 在同一次 status UPDATE 中原子释放；
- `POST /api/v1/workflows/executions/{execution_id}/resume` HTTP Resume API；
- Execution HTTP response 增加 `resume_of_execution_id + resume_checkpoint_sequence` lineage 字段；
- `tests/unit/test_workflow_resume_api_contract.py`：Resume API route / role / Domain Service delegation 单元覆盖；
- `tests/api_real/test_workflow_resume_api.py`：真实 HTTP + PostgreSQL + 独立 Worker Resume 验收；
- `tests/api_real/test_workflow_resume_dag_api.py`：线性 DAG Resume frontier 验收；
- `tests/api_real/test_workflow_resume_failure_api.py`：failure-after-resume lineage / terminal boundary 验收；
- Tenant Safe Real API Source Baseline Gate；
- Worker Resume DAG Definition 提前裁剪问题已记录到 `docs/04-errors/2026-08-26-durable-resume-worker-dag-definition-truncation.md`；
- `WorkflowExecutionRecoveryPolicy`：集中定义自动恢复最大次数、冷却时间及状态 / ownership / Checkpoint 安全边界；
- `WorkflowExecutionRecoveryPolicyEvaluator`：纯规则、无数据库副作用的自动恢复决策入口；
- 默认自动恢复策略：`max_attempts=3`、`cooldown_seconds=60`；
- `WorkflowExecutionAutomaticRecoveryService`：串联 Checkpoint Candidate、Resume lineage 次数、Recovery Policy 与正式 `WorkflowExecutionService.resume_from_latest_checkpoint()`；
- 自动恢复不修改 Source failed 状态、不获取 Worker ownership、不直接启动 Runtime；
- 自动恢复 Resume 继续使用正式 deterministic idempotency key，Worker 仍从 pending claim 路径执行；
- 自动恢复次数沿 `resume_of_execution_id` lineage 计算，与普通 Retry 次数保持独立；
- `WorkflowRecoveryScheduler`：Scheduler 侧独立 Recovery Scan，发现 failed Execution 后只委托 Recovery Domain，不复制恢复规则；
- Recovery Scan 使用独立数据库 Session 逐 Execution 处理，保持 tenant scope 与并发幂等边界；
- Recovery Scan 输出 `candidates / eligible / recovered / rejected / contention / failed` 聚合指标；
- `tests/unit/test_workflow_recovery_policy.py`：覆盖 disabled / failed / ownership / Checkpoint / cooldown / max-attempts 边界；
- `tests/unit/test_workflow_automatic_recovery_service.py`：覆盖 Recovery Policy + Candidate Domain 编排边界；
- `tests/unit/test_workflow_recovery_scheduler.py`：覆盖 Scheduler Recovery Scan 委托边界。

## Durable Recovery Policy Contract

```text
failed Execution
      ↓
active Worker ownership? ── yes → reject
      ↓ no
valid completed-node Checkpoint? ── no → reject
      ↓ yes
max recovery attempts reached? ── yes → reject
      ↓ no
cooldown elapsed? ── no → reject + retry_after
      ↓ yes
create deterministic pending Resume Execution
      ↓
Worker normal claim / lease / Runtime
```

规则：

1. 自动恢复只接受 `failed` Execution；`running` 不允许直接通过 Recovery Policy 复活。
2. `worker_owner != NULL` 时拒绝自动恢复，避免绕过 ownership fencing。
3. Checkpoint 必须满足 `node.completed + execution.running` 的既定恢复边界。
4. 默认最多 3 次 Resume lineage 尝试；达到上限后保持 failed，不再自动生成 Resume。
5. Source failed 后默认等待 60 秒冷却窗口，防止 Scheduler 高频轮询重复恢复。
6. `max_attempts=0` 表示关闭自动恢复，不影响人工 Resume API。
7. 自动恢复次数沿 `resume_of_execution_id` lineage 统计，不与 `retry_of_execution_id` 的人工 Retry 混为一谈。
8. Recovery Policy 本身纯规则、无数据库副作用；实际创建 Resume 必须继续调用正式 Domain Service。
9. Recovery Domain 不直接启动 WorkflowRuntime；新 Execution 必须重新进入 Worker claim。
10. deterministic Resume idempotency key 与数据库唯一约束继续作为最终幂等兜底。

## Scheduler Recovery Scan Contract

```text
Scheduler tick
    ↓
query failed + worker_owner IS NULL
    ↓
Recovery Domain evaluate()
    ├── rejected → count + continue
    └── eligible
          ↓
       Recovery Domain recover()
          ↓
       lock Source Execution
          ↓
       Resume Candidate revalidation
          ↓
       deterministic idempotency
          ↓
       new pending Resume Execution
          ↓
       Worker normal claim
```

Scheduler 明确不负责：

- 复制 `max_attempts` / cooldown / Checkpoint 判断；
- 直接修改 failed → pending；
- 直接创建 Resume Execution；
- 抢 Worker ownership；
- 启动 WorkflowRuntime。

多个 Scheduler 实例可以同时扫描同一 failed Execution，最终结果依靠 Source Execution lock、deterministic idempotency key 和数据库唯一约束收敛。

## 当前开发策略

按当前开发要求，暂停完整测试流程，不把 Backend Regression、Frontend Gate、Browser E2E、Real API Acceptance 或服务重启作为本轮主线开发门槛。开发阶段只要求新增 / 修改代码的单元测试通过，并继续直接推进主线实现。

Real API / Worker 验收脚本仍必须保持可重复执行，但当前不作为主线阻塞项；真实联调仍由开发者人工启动 API / Scheduler / Worker 服务，测试脚本不得控制服务生命周期。

## 本轮新增测试状态

本轮新增单元测试源码已经提交，但由于当前执行环境无法直接访问仓库运行本地 `uv run pytest`，**不得将本轮新增测试标记为已通过**。上一轮开发者实际反馈的稳定基线继续保留为历史事实：

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

1. 将 `WorkflowRecoveryScheduler.scan_once()` 接入现有 Scheduler Runtime 主循环，保持与 Scheduled Trigger Dispatch 独立计数与异常隔离。
2. 为 Recovery Scan 增加最小轮询周期 / scan limit / tenant-safe contention 指标 Contract，并继续保持 Recovery Policy 单一入口。
3. 完成自动恢复 Scheduler Contract 后，再进入自动恢复 Real API / Worker 验收；当前阶段仍不以该验收阻塞主线。
4. 自动恢复稳定后，再冻结 DAG 分支状态合并 Contract，并实现多 frontier Resume。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract、Recovery Policy、Automatic Recovery Domain、Recovery Scheduler Scan、Resume Planner、Worker Resume Runtime 与 HTTP Resume API 都属于 API / Worker / Scheduler 进程内代码变更。代码更新后必须由开发者人工重启受影响服务，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。
