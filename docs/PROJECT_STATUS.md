# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；当前已完成 Checkpoint 数据模型、0032 migration、Checkpoint Service 与 targeted unit tests，尚未接入 Runtime 自动 checkpoint / resume。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

```text
b8cba41 test(worker): align heartbeat retry test with ownership exit contract
```

Phase 2.5 最终本地结果：

```text
Worker targeted Unit: 13 passed in 1.23s
Backend Regression: 417 passed, 3 skipped, 36 deselected in 29.44s
Tenant Safe Real API: 35 passed in 63.01s
Scheduler / Worker Recovery Acceptance: 1 passed
```

这些结果均来自开发者本地实际执行。

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
Node / Execution terminal state
   ↓
Audit / Trace / ownership cleanup
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowRuntime 负责“如何执行节点”。**

## Phase 2.6 Durable Execution Checkpoint Foundation

当前目标：

```text
WorkflowExecution
      ↓
Checkpoint Service
      ↓
PostgreSQL immutable checkpoint
      ↓
后续 Durable Resume / Recovery
```

本轮已实现：

- Migration `0032_workflow_execution_checkpoint`；
- `WorkflowExecutionCheckpoint` 不可变快照模型；
- `WorkflowExecutionCheckpointService.append()`；
- `WorkflowExecutionCheckpointService.latest()`；
- `execution_id + sequence` 唯一约束；
- Checkpoint targeted unit tests。

明确不在当前范围：

- 自动 Resume；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing。

## 当前验收要求

Phase 2.6 必须先完成：

1. `uv run alembic upgrade head` 实际验证 `0032_workflow_execution_checkpoint`；
2. Checkpoint targeted unit tests；
3. 真实 PostgreSQL persistence Gate；
4. Runtime Node completion boundary 接入；
5. durable resume 的 ownership / version / idempotency 设计与实现。

在以上步骤完成前，不得将 durable resume 标记为完成。

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换；
- 禁止通过数据库 reset 掩盖 Worker recovery 问题；
- 禁止新增平行 Workflow Runtime 或第二套 Provider；
- 禁止使用 GitHub Actions 结果替代本地 Gate；
- 禁止 Real API Gate 自动启动、停止或重启 API / Scheduler / Worker；
- 禁止 lease 到期后旧 Worker 自行复活 ownership；
- 禁止在 Phase 2.6 中未经设计评审直接增加自动 Resume。
