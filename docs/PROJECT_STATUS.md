# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Execution Contract、第一版顺序 Runtime Resume、真实 PostgreSQL + 独立 Worker 的 Resume Acceptance 与 failure-after-resume Acceptance 已完成；当前继续收敛 DAG Resume Runtime Integration 的拓扑与完成事实安全边界。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前 main 已进入 DAG Resume Runtime Integration：Source failed Execution 的 Checkpoint 恢复边界由 Worker 重新校验，完整 Workflow Version Definition 交给 WorkflowRuntime，由 Runtime 根据 Source Node 完成事实计算真实 Resume frontier。Worker 提前裁剪 Definition 的问题已修复；当前进一步冻结第一版 DAG Resume 的单一 root 与 completed predecessor 闭包约束，避免不可能由顺序 Runtime 产生的持久化完成事实进入恢复规划。

## 当前产品级执行架构

```text
API Service
   ↓
Trigger Domain
   ↓
Scheduler Service
   ↓
PostgreSQL pending WorkflowExecution
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
       新 Checkpoint append
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowExecutionService 负责执行状态机与 Resume 安全边界，WorkflowRuntime 负责“如何执行节点”和当前 DAG Resume frontier 选择，Checkpoint 负责“记录已完成执行事实”，Resume Candidate assessment 负责“判断是否满足恢复前置条件”，Resume Execution contract 负责“创建新的 pending 恢复任务并固定来源事实”。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `0033_workflow_execution_resume_contract`；
- `WorkflowExecutionCheckpoint` 不可变快照模型；
- `WorkflowExecutionCheckpointService.append()`；
- `WorkflowExecutionCheckpointService.append_next_in_transaction()`；
- `WorkflowExecutionCheckpointService.latest()`；
- `Node completed` 自动生成 Checkpoint；
- Node 状态与 Checkpoint 同事务提交；
- `execution_id + sequence` 数据库唯一约束；
- Checkpoint 集成单元测试；
- Real API + PostgreSQL persistence 验收测试；
- Real API Checkpoint Gate 改为每轮新建 Execution，避免历史 Execution 与旧进程污染验收；
- `WorkflowExecutionCheckpointRecoveryService`：只读 Resume Candidate 评估；
- Resume Candidate 固定原 Execution Workflow Version；
- Resume Candidate 拒绝 `running` Execution 与 active Worker ownership；
- Resume Candidate 使用 `execution_id + checkpoint.sequence` 生成确定性幂等键；
- `WorkflowExecutionService.resume_from_latest_checkpoint()`：创建新的 pending Resume Execution；
- Resume Execution 持久化 `resume_of_execution_id + resume_checkpoint_sequence`；
- Resume Execution 固定原 Workflow Version；
- Resume Execution 使用 deterministic idempotency key，并由 `tenant_id + idempotency_key` 唯一约束兜底；
- Source failed Execution 保持失败状态；
- Resume Execution 不直接抢 Worker lease、不直接启动 WorkflowRuntime；
- `WorkflowExecutionResumePlanner`：纯内存计算 Checkpoint 后续顺序 nodes；
- DAG Resume Contract / Frontier Planner / Runtime Planner / Linear Sequence Planner；
- DAG Resume Contract 第一版只接受单一 root；
- DAG Resume Planner 拒绝 predecessor 尚未完成的非闭包完成事实；
- Worker 在执行 Resume 前重新校验 Source / Checkpoint / Version；
- Worker 使用 Checkpoint `state_data` 作为 Resume Execution 的 Runtime 输入；
- Worker Resume 准备阶段保留完整 DAG Definition，由 WorkflowRuntime 统一计算 Resume frontier；
- 第一版 DAG Runtime 仍只允许单一 frontier，分支状态合并 Contract 未冻结前明确拒绝多个 frontier；
- Worker 并发任务显式传递自己的数据库 Session，禁止实例级共享 Session；
- `tests/api_real/test_workflow_resume_api.py`：真实 HTTP 创建 Source、真实 PostgreSQL Checkpoint、正式 Resume Domain Service、新 pending Resume Execution、独立 Worker 顺序恢复与 Resume Checkpoint 验证；
- `tests/api_real/test_workflow_resume_failure_api.py`：真实 HTTP + PostgreSQL + 独立 Worker failure-after-resume lineage / terminal boundary 验证；
- `scripts/test/api-real/05_run_durable_resume_real_tests.ps1`：只验证并使用开发者人工启动的 API / Worker，不控制服务生命周期；
- Tenant Safe Real API Source Baseline Gate；
- Worker Resume DAG Definition 提前裁剪问题已记录到 `docs/04-errors/2026-08-26-durable-resume-worker-dag-definition-truncation.md`，并补充 Worker 单元回归测试。

## Phase 2.6 设计边界

当前明确不实现：

- DAG 分支 Resume；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- Resume Service 直接启动 Runtime；
- 自动恢复失败 Execution。

## 本地实际验收结果

开发者已实际反馈的上一稳定基线：

```text
DAG / Resume targeted unit tests
40 passed in 1.08s

uv run pytest -q
466 passed, 3 skipped, 39 deselected in 32.08s

05_run_durable_resume_real_tests.ps1
success real_api: 1 passed in 4.33s
failure-boundary real_api: 1 passed in 2.17s
```

以上为开发者实际反馈的上一稳定基线；本次新增 DAG Contract / Planner 边界修复后的测试结果尚未由开发环境重新执行，因此不得把它们标记为本次修复的通过证据。

## 下一步

1. 在本地执行 DAG Contract / Planner / Runtime targeted tests，确认新增单 root 与 completed predecessor 闭包约束；
2. 执行 `uv run pytest -q`，确认 Backend Regression 未回归；
3. 重启最新 main 的 API Service 与 Worker Service，使进程载入当前 Runtime 代码；
4. 执行 `05_run_durable_resume_real_tests.ps1`，确认真实 PostgreSQL + HTTP + 独立 Worker 的 success / failure acceptance；
5. 在单一 frontier acceptance 稳定后，继续补齐 DAG Runtime integration / failure boundary；
6. 在 DAG 恢复安全边界稳定后，再评估 HTTP Resume API；
7. 自动恢复仅在 ownership、checkpoint、planner、终态与 DAG 边界全部稳定后进入设计。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract、Resume Planner 与 Worker Resume Runtime 都属于 API / Worker 进程内代码变更。代码更新后必须由开发者人工重启受影响的 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。
