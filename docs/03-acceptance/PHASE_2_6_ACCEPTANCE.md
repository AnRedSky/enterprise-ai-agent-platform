# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 WorkflowRuntime 的 Node completion 已形成真实 PostgreSQL Checkpoint 持久化边界，并验证后续 Durable Resume 前置条件已经以只读规则固定：

```text
Worker / HTTP Runtime
        ↓
WorkflowExecutionService.transition_node(completed)
        ↓
Node state + Checkpoint append
        ↓
同一 PostgreSQL transaction commit
        ↓
只读 Resume Candidate assessment
```

Checkpoint 不承担 Resume、调度或 ownership 决策；Resume Candidate assessment 也不修改生产状态。

## 2. 自动化入口

### Checkpoint targeted unit

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_workflow_execution_checkpoint.py `
  tests/unit/test_workflow_checkpoint_integration.py `
  tests/unit/test_workflow_checkpoint_recovery.py
```

### Backend Regression

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

### Tenant Safe Real API

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

### Checkpoint Real PostgreSQL persistence

```powershell
cd backend
uv run pytest -q tests/api_real/test_workflow_checkpoint_api.py
```

该测试要求预先准备 Real API、Worker 与 PostgreSQL；不会启动、停止或重启任何服务。

## 3. 服务版本前置

Checkpoint 是 API / Worker 进程内的 Python 代码。服务进程已经启动后再更新代码，旧进程不会自动载入新的 Checkpoint Runtime 实现。因此 **Runtime Checkpoint 代码变更后，必须人工重启受影响的 API Service 与 Worker Service，再执行 Real API Gate**。

测试 Gate 本身禁止进行服务生命周期控制：

```text
代码更新
   ↓
人工重启 API Service
   ↓
人工重启 Worker Service
   ↓
运行 Gate
```

推荐本地启动：

```powershell
# Terminal 1
uv run python run.py

# Terminal 2
uv run python run_worker.py
```

Scheduler 对本次 Checkpoint persistence gate 不是必需依赖，但现有 Scheduler 若继续运行可以保持不变；不得为了测试脚本自动重启 Scheduler。

## 4. 数据库前置

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期：

```text
0032_workflow_execution_checkpoint (head)
```

本次 Resume Candidate assessment 不新增数据库结构，因此不要求新的 migration。

## 5. Node completion 断言

必须满足：

```text
Node running
    ↓
transition_node(..., completed)
    ↓
Checkpoint sequence = Execution 当前最大 sequence + 1
    ↓
Node + Checkpoint 同事务提交
```

禁止：

```text
Node committed
Checkpoint commit failed / missing
```

## 6. Real PostgreSQL 断言

Real API Checkpoint Gate **每轮都会新建一个 Execution 并立即执行**，不再依赖 bootstrap 阶段历史 `WORKFLOW_EXECUTION_ID`，避免旧 Execution 污染验收结果。

真实 HTTP Execution 完成后，PostgreSQL 中必须存在：

```text
execution_id = 本轮新建 HTTP Execution ID
checkpoint_reason = node.completed
node_status = completed
sequence = 0..N 连续递增
```

测试必须读取真实 PostgreSQL，而不能使用 JSON fixture 或进程内 Mock 数据代替。

## 7. Resume Candidate targeted 断言

新的 `WorkflowExecutionCheckpointRecoveryService` 仅做只读评估，必须验证：

```text
failed Execution + 无 active worker_owner
        ↓
最新 Checkpoint 存在
        ↓
checkpoint_reason = node.completed
checkpoint.execution_status = running
checkpoint.node_status = completed
checkpoint.node_id != null
        ↓
eligible = true
resume key = resume:<execution_id>:checkpoint:<sequence>
```

同时必须拒绝：

```text
running Execution
active worker_owner
Checkpoint 缺失
checkpoint_reason != node.completed
Checkpoint completion boundary 不完整
```

## 8. 禁止验收方式

- 不得通过 Mock Checkpoint Service 作为唯一完成依据；
- 不得通过手工向 `workflow_execution_checkpoints` 插入数据证明 Runtime 已接入；
- 不得修改 `running → running` 状态机；
- 不得让 Gate 自动启动 / 停止 / 重启 API、Scheduler、Worker；
- 不得把 Checkpoint 自动 Resume 能力提前混入本阶段；
- 不得把 Resume Candidate assessment 当成实际 Resume；
- 不得使用服务重启前产生的历史 Execution 作为 Runtime Checkpoint 接入验收的唯一证据。

## 9. 当前状态

`0032` migration、Checkpoint 基础服务、Runtime Node completion 接入以及 Resume Candidate 只读评估基线已提交到 `main`。开发者必须：

1. 同步最新 `main`；
2. 人工重启 API / Worker，使运行进程加载最新代码；
3. 执行 Checkpoint targeted / Backend / Real PostgreSQL Gate；
4. 验证 Resume Candidate targeted tests；
5. 再决定本 Acceptance 是否可以进入最终 Passed 状态。
