# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate、Resume Execution Contract、第一版顺序 Runtime Resume、真实 PostgreSQL + 独立 Worker 的 Resume Acceptance 与 failure-after-resume Acceptance 已完成；当前正在收敛 DAG Resume Runtime Integration。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前 main 已进入 DAG Resume Runtime Integration：Source failed Execution 的 Checkpoint 恢复边界由 Worker 重新校验，完整 Workflow Version Definition 交给 WorkflowRuntime，由 Runtime 根据 Source Node 完成事实计算真实 Resume frontier。此前 Worker 提前裁剪 Definition 导致真实 Resume 无法完成的问题已修复，并补充了 Worker 单元回归测试与错误记录。真实 PostgreSQL + 独立 Worker 的修复后 acceptance 需要开发者重启 API / Worker 后重新执行确认。

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
       WorkflowRuntime DAG Resume Planner
          ↓
       当前单一 frontier Node
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
- Worker 在执行 Resume 前重新校验 Source / Checkpoint / Version；
- Worker 使用 Checkpoint `state_data` 作为 Resume Execution 的 Runtime 输入；
- Worker Resume 准备阶段保留完整 DAG Definition，由 WorkflowRuntime 统一计算 Resume frontier；
- 第一版 DAG Runtime 仍只允许单一 frontier，分支状态合并 Contract 未冻结前明确拒绝多个 frontier；
- Worker 并发任务显式传递自己的数据库 Session，禁止实例级共享 Session；
- `tests/api_real/test_workflow_resume_api.py`：真实 HTTP 创建 Source、真实 PostgreSQL Checkpoint、正式 Resume Domain Service、新 pending Resume Execution、独立 Worker 顺序恢复与 Resume Checkpoint 验证；
- `tests/api_real/test_workflow_resume_failure_api.py`：真实 HTTP + PostgreSQL + 独立 Worker failure-after-resume lineage / terminal boundary 验证；
- `scripts/test/api-real/05_run_durable_resume_real_tests.ps1`：只验证并使用开发者人工启动的 API / Worker，不控制服务生命周期；
- Tenant Safe Real API Source Baseline Gate；
- 两个新增 Real API 验收测试模块已补充中文模块职责说明，符合 Backend 模块说明规则；
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

开发者于 2026-08-26 已实际反馈修复前基线：

```text
DAG targeted unit tests
32 passed in 0.91s

uv run pytest -q
464 passed, 3 skipped, 39 deselected in 30.30s

05_run_durable_resume_real_tests.ps1
修复前：success real_api 在等待 Resume Execution completed 时超时；failure-boundary 尚未进入本轮结果。
```

上述结果属于修复前事实，不能作为当前修复后的通过证据。当前修复后的本地测试结果必须由开发者重新执行并记录；在此之前不得标记为 acceptance passed。

## 下一步

1. 重启最新 main 的 API Service 与 Worker Service，使进程载入本次 Worker Resume 修复；
2. 执行 Worker targeted unit tests 与 Backend Regression；
3. 执行 `05_run_durable_resume_real_tests.ps1`，确认真实 PostgreSQL + HTTP + 独立 Worker 的 success / failure acceptance；
4. 若 DAG 单一 frontier Runtime acceptance 通过，继续补齐 DAG Runtime integration / failure boundary；
5. 在 DAG 恢复安全边界稳定后，再评估 HTTP Resume API；
6. 自动恢复仅在 ownership、checkpoint、planner、终态与 DAG 边界全部稳定后进入设计。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract、Resume Planner 与 Worker Resume Runtime 都属于 API / Worker 进程内代码变更。代码更新后必须由开发者人工重启 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。
