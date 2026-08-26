# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate 只读评估、Resume Execution 创建契约及第一版顺序 Runtime Resume 已完成；DAG 分支 Resume 与自动恢复尚未实现。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

本轮继续推进 Durable Resume Runtime，新增 Resume Planner 与 Worker → Runtime 顺序恢复边界。此前 Backend / Real API 验收基线均已通过，新的本轮测试结果以开发者本地实际执行为准，不在此预填。

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
- Worker 并发任务显式传递自己的数据库 Session，禁止实例级共享 Session。

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

## 下一步

1. 真实 PostgreSQL 验证 Resume Execution persistence 与幂等收敛；
2. 真实 Worker 验证 Resume claim / lease / fencing；
3. 验证 Resume 后 Checkpoint sequence 连续性与最终状态；
4. 评估并实现 DAG Runtime 恢复规划；
5. 完成上述边界后再评估 HTTP Resume 与自动恢复。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate、Resume Execution Contract 与 Resume Planner 都属于 API / Worker 进程内代码变更。代码更新后必须由开发者人工重启 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。