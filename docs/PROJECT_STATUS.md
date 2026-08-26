# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**开发中；Checkpoint 模型、0032 migration、Checkpoint Service、Node completed 同事务接入及 Resume Candidate 只读评估基线已完成；自动 Resume 尚未实现。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

```text
57e2b4d feat(durable): establish resume candidate safety boundary
```

最近一次开发者本地验收：

```text
Checkpoint + Resume Candidate targeted: 8 passed, 4 warnings
Backend Regression: 425 passed, 3 skipped, 37 deselected, 4 warnings
Migration head: 0032_workflow_execution_checkpoint
Tenant Safe Real API: 36 passed, 1 failed
```

本次本地反馈中已完成根因确认：

1. Resume Candidate 单元测试使用 `datetime.utcnow()`，产生 Python 弃用警告；已改为 timezone-aware UTC 时间构造。
2. Runtime Model Governance Real API 测试直接触发 `/run` 时没有统一处理独立 Worker 先 claim 的合法 `409` ownership race；已改用现有 `run_or_observe_execution`，不复制第二套竞态处理规则。
3. `uv run pytest -q tests/api_real/test_runtime_model_governance_api.py` 无 Real API Context 时被 deselect / context failure，不能作为 Gate 通过依据；唯一正式入口仍为 Tenant Safe Real API Gate。

以上修复提交后需要开发者重新执行完整本地 Gate，当前文档不预填修复后的测试结果。

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
             后续 Durable Resume / Recovery
```

核心职责冻结：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，WorkflowRuntime 负责“如何执行节点”，Checkpoint 负责“记录已完成执行事实”，Resume Candidate assessment 负责“判断是否满足未来恢复前置条件”，但不执行恢复。**

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
- Real API + PostgreSQL persistence 验收测试；
- Real API Checkpoint Gate 改为每轮新建 Execution，避免历史 Execution 与旧进程污染验收；
- `WorkflowExecutionCheckpointRecoveryService`：只读 Resume Candidate 评估；
- Resume Candidate 固定原 Execution Workflow Version；
- Resume Candidate 拒绝 `running` Execution 与 active Worker ownership；
- Resume Candidate 使用 `execution_id + checkpoint.sequence` 生成确定性幂等键基础；
- Runtime Model Governance Real API 测试复用统一 Worker claim race helper；
- Resume Candidate 测试移除 `datetime.utcnow()` 弃用警告。

## Phase 2.6 设计边界

当前明确不实现：

- 自动 Resume；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP Resume API；
- 绕过 Worker ownership fencing；
- 用 Checkpoint 替代 Node 状态机；
- 让 Resume Candidate assessment 直接创建 Execution 或启动 Runtime。

## 服务版本验收边界

Checkpoint Runtime 接入与 Resume Candidate 评估都属于进程内代码变更。代码更新后，必须由开发者人工重启 API Service 与 Worker Service，使进程载入最新代码；Real API / Backend Gate 绝不负责启动、停止或重启服务。

```text
代码更新
   ↓
人工重启 API Service
   ↓
人工重启 Worker Service
   ↓
Real API / Backend Gate
```

当前推荐：

```powershell
uv run python run.py
uv run python run_worker.py
```

## 当前验收要求

Runtime Checkpoint / Resume Candidate 接入后必须重新执行：

1. Checkpoint + Resume Candidate targeted tests；
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
- 禁止在 Phase 2.6 中未经设计评审直接增加自动 Resume；
- 禁止把 Resume Candidate assessment 当成实际 Resume。
