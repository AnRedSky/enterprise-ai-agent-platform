# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint、Resume Candidate 只读评估、Resume Execution 创建契约已完成；自动从 Checkpoint 继续执行尚未实现。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

```text
5c15c7c docs(error): record scheduler deadlock and persisted execution response contract
```

最近一次开发者本地验收反馈：

```text
Targeted Worker / Checkpoint: 18 passed
Backend Regression: 425 passed, 3 skipped, 37 deselected
Tenant Safe Real API: 36 passed
Scheduler / Worker persisted recovery acceptance: 1 passed
```

本轮闭环情况：

1. Runtime Model Governance Real API 的合法 Worker claim race 已统一通过 `run_or_observe_execution()` 观察真实 PostgreSQL 终态，不再直接读取 HTTP 错误体作为 Execution。
2. Scheduler recovery 出现的 PostgreSQL `DeadlockDetectedError` 已通过拆分 Schedule lease / Slot+Execution / Schedule advancement 三阶段事务边界解决。
3. Real API Source Baseline Gate 已验证关键测试源码与远端 `main` 一致，并保持调用目录独立性。

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
   ↓
WorkflowRuntime
   ↓
Node transition
   ├── failed / running / skipped
   └── completed → Checkpoint append (same transaction)
                    ↓
             PostgreSQL immutable checkpoint
                    ↓
             Read-only Resume Candidate assessment
                    ↓
             New pending Resume Execution
                    ↓
             后续 Durable Resume Runtime（未开放）
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowRuntime 负责“如何执行节点”，Checkpoint 负责“记录已完成执行事实”，Resume Candidate assessment 负责“判断是否满足恢复前置条件”，Resume Execution contract 负责“创建新的 pending 恢复任务并固定来源事实”，但当前仍不直接执行恢复。**

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
- Resume Candidate 使用 `execution_id + checkpoint.sequence` 生成确定性幂等键基础；
- `WorkflowExecutionService.resume_from_latest_checkpoint()`：创建新的 pending Resume Execution；
- Resume Execution 持久化 `resume_of_execution_id + resume_checkpoint_sequence`；
- Resume Execution 固定原 Workflow Version；
- Resume Execution 使用 deterministic idempotency key，并由 `tenant_id + idempotency_key` 唯一约束兜底；
- Source failed Execution 保持失败状态；
- Resume Execution 不直接抢 Worker lease、不直接启动 WorkflowRuntime。

## Phase 2.6 设计边界

当前明确不实现：

- 自动从 Checkpoint 继续执行；
- Runtime 根据 Checkpoint 跳过已完成 Node；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- Resume Service 直接启动 Runtime。

## 下一步

1. 通过真实 PostgreSQL 验证 Resume Execution persistence 与幂等收敛；
2. 验证 Resume Execution 被标准 Worker claim / lease / ownership fencing 路径正常领取；
3. 在 Runtime 建立 `resume_checkpoint_sequence` 对应的确定性起点；
4. 支持顺序 / DAG 节点状态重建后再执行剩余 Node；
5. 完成后再评估 HTTP Resume 与自动恢复。

## 服务版本验收边界

Checkpoint Runtime、Resume Candidate 与 Resume Execution Contract 都属于 API / Worker 进程内代码变更。代码更新后必须由开发者人工重启 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。
