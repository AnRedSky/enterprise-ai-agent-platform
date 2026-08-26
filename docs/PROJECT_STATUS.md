# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Execution Contract、第一版顺序 Runtime Resume、真实 PostgreSQL + 独立 Worker 的 Resume Acceptance 与 failure-after-resume Acceptance 均已完成；下一边界为 DAG Resume Contract 与图恢复规划器。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前 main 已完成 Ordered Runtime Resume 的生产代码路径：Source failed Execution 的 Checkpoint 恢复边界由 Worker 重新校验，Resume Planner 生成剩余顺序 Nodes，Worker 使用独立数据库 Session 消费新的 pending Resume Execution。开发者已实际执行 Durable Resume Acceptance 与 failure-after-resume Acceptance，真实 PostgreSQL、真实 HTTP、独立 Worker 链路均通过。本地直接针对 `api_real` 文件执行 pytest 时必须显式使用 `-m real_api`，否则默认 `addopts` 会将 Real API 测试 deselect，这属于既定测试隔离行为。

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
       Resume Planner
          ↓
       Checkpoint state_data
          ↓
       剩余顺序 Nodes
          ↓
       WorkflowRuntime
          ↓
       新 Checkpoint append
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowExecutionService 负责执行状态机与 Resume 安全边界，WorkflowRuntime 负责“如何执行节点”，Checkpoint 负责“记录已完成执行事实”，Resume Candidate assessment 负责“判断是否满足恢复前置条件”，Resume Execution contract 负责“创建新的 pending 恢复任务并固定来源事实”，Resume Planner 负责“把 Checkpoint 转换为当前顺序 Runtime 的起点”，但不执行 DAG 分支恢复。**

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
- Worker 在执行 Resume 前重新校验 Source / Checkpoint / Version；
- Worker 使用 Checkpoint `state_data` 作为 Resume Execution 的 Runtime 输入；
- 第一版 Resume Runtime 从 checkpoint node 之后继续执行；
- Worker 并发任务显式传递自己的数据库 Session，禁止实例级共享 Session；
- `tests/api_real/test_workflow_resume_api.py`：真实 HTTP 创建 Source、真实 PostgreSQL Checkpoint、正式 Resume Domain Service、新 pending Resume Execution、独立 Worker 顺序恢复与 Resume Checkpoint 验证；
- `tests/api_real/test_workflow_resume_failure_api.py`：真实 HTTP + PostgreSQL + 独立 Worker failure-after-resume lineage / terminal boundary 验证；
- `scripts/test/api-real/03_run_durable_resume_acceptance.ps1`：只验证并使用开发者人工启动的 API / Worker，不控制服务生命周期；
- `scripts/test/api-real/04_run_durable_resume_failure_acceptance.ps1`：只验证并使用开发者人工启动的 API / Worker，不控制服务生命周期；
- Tenant Safe Real API Source Baseline Gate；
- 两个新增 Real API 验收测试模块已补充中文模块职责说明，符合 Backend 模块说明规则。

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

开发者于 2026-08-26 实际反馈：

```text
uv run pytest -q
438 passed, 3 skipped, 39 deselected in 31.09s

03_run_durable_resume_acceptance.ps1
1 passed in 4.31s

04_run_durable_resume_failure_acceptance.ps1
1 passed in 2.15s
```

两次 Real API Gate 均确认 `HEAD == origin/main: 49d3cac3bb65fc110689c438753accde59b09d52`，关键 Real API / Checkpoint 测试源码干净，Runtime Model Governance 使用统一 claim-race helper，Checkpoint Resume Candidate 测试不使用 `datetime.utcnow()`。

## 下一步

1. 冻结 Phase 2.6 DAG Resume Runtime 恢复 Contract（GitHub Issue #49）；
2. 在 Contract 冻结后实现 DAG Resume Planner，先完成纯内存 Planner 单元测试；
3. 将 Planner 接入 Runtime，建立 DAG integration / failure boundary；
4. 执行真实 PostgreSQL + 独立 Worker 的 DAG Resume Acceptance；
5. DAG 恢复安全边界稳定后，再评估 HTTP Resume API；
6. 自动恢复仅在 ownership、checkpoint、planner、终态与 DAG 边界全部稳定后进入设计。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract、Resume Planner 与 Worker Resume Runtime 都属于 API / Worker 进程内代码变更。代码更新后必须由开发者人工重启 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。