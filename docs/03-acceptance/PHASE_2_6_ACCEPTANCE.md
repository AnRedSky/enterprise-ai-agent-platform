# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 WorkflowRuntime 的 Node completion 已形成真实 PostgreSQL Checkpoint 持久化边界：

```text
Worker / HTTP Runtime
        ↓
WorkflowExecutionService.transition_node(completed)
        ↓
Node state + Checkpoint append
        ↓
同一 PostgreSQL transaction commit
```

Checkpoint 不承担 Resume、调度或 ownership 决策。

## 2. 自动化入口

### Checkpoint targeted unit

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_checkpoint.py tests/unit/test_workflow_checkpoint_integration.py
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

该测试要求预先准备 Real API 与 PostgreSQL；不会启动、停止或重启任何服务。

## 3. 数据库前置

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期：

```text
0032_workflow_execution_checkpoint (head)
```

## 4. Node completion 断言

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

## 5. Real PostgreSQL 断言

真实 HTTP Execution 完成后，PostgreSQL 中必须存在：

```text
execution_id = HTTP Execution ID
checkpoint_reason = node.completed
node_status = completed
sequence = 0..N 连续递增
```

测试必须读取真实 PostgreSQL，而不能使用 JSON fixture 或进程内 Mock 数据代替。

## 6. 禁止验收方式

- 不得通过 Mock Checkpoint Service 作为唯一完成依据；
- 不得通过手工向 `workflow_execution_checkpoints` 插入数据证明 Runtime 已接入；
- 不得修改 `running → running` 状态机；
- 不得让 Gate 自动启动 / 停止 / 重启 API、Scheduler、Worker；
- 不得把 Checkpoint 自动 Resume 能力提前混入本阶段。

## 7. 当前状态

`0032` migration、Checkpoint 基础服务和本地 targeted tests 已完成；Runtime Node completion 接入已提交到 `main`。开发者必须重新执行本次新增 targeted / Backend / Real PostgreSQL Gate 后，才能将本 Acceptance 标记为最终 Passed。
