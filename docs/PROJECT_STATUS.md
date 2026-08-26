# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；已完成 Checkpoint 模型、0032 migration、Checkpoint Service，并已接入 Node completed 事务边界；自动 Resume 尚未实现。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

```text
fbea604 feat(durable): add workflow execution checkpoint foundation
```

最新开发者本地验收：

```text
Checkpoint targeted unit: 3 passed in 0.95s
Backend Regression: 420 passed, 3 skipped, 36 deselected in 30.49s
Tenant Safe Real API: 35 passed in 63.27s
Migration head: 0032_workflow_execution_checkpoint
```

以上结果均来自开发者本地实际执行；本次 Runtime Checkpoint 接入后的新 targeted / full Gate 尚未重新执行，因此不得预填为通过。

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
             Audit / Trace / ownership cleanup
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowRuntime 负责“如何执行节点”，Checkpoint 负责“记录已完成执行事实”。**

## Phase 2.6 当前实现

- `0032_workflow_execution_checkpoint`；
- `WorkflowExecutionCheckpoint` 不可变快照模型；
- `WorkflowExecutionCheckpointService.append()`；
- `WorkflowExecutionCheckpointService.append_next_in_transaction()`；
- `WorkflowExecutionCheckpointService.latest()`；
- `Node completed` 自动生成 Checkpoint；
- Node 状态与 Checkpoint 同事务提交；
- `execution_id + sequence` 数据库唯一约束；
- Checkpoint 集成单元测试；
- Real API + PostgreSQL persistence 验收测试入口。

## Phase 2.6 设计边界

当前明确不实现：

- 自动 Resume；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机。

## 当前验收要求

Runtime Checkpoint 接入后必须重新执行：

1. Worker / Checkpoint targeted tests；
2. `uv run pytest -q`；
3. `uv run alembic upgrade head` + `uv run alembic current`；
4. Tenant Safe Real API；
5. Real API + PostgreSQL Checkpoint persistence；
6. Worker Runtime consistency diagnostic；
7. Scheduler / Worker Recovery Acceptance。

在上述新代码完成本地实际验证前，不得将 Phase 2.6 标记为 Passed。

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换；
- 禁止通过数据库 reset 掩盖 Worker recovery 问题；
- 禁止新增平行 Workflow Runtime 或第二套 Provider；
- 禁止使用 GitHub Actions 结果替代本地 Gate；
- 禁止 Real API Gate 自动启动、停止或重启 API / Scheduler / Worker；
- 禁止 lease 到期后旧 Worker 自行复活 ownership；
- 禁止在 Phase 2.6 中未经设计评审直接增加自动 Resume。
