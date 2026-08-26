# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 WorkflowRuntime 的 Node completion 已形成真实 PostgreSQL Checkpoint 持久化边界，并验证 Durable Resume 的 Execution 创建安全契约：

```text
Worker / HTTP Runtime
        ↓
WorkflowExecutionService.transition_node(completed)
        ↓
Node state + Checkpoint append
        ↓
同一 PostgreSQL transaction commit
        ↓
Resume Candidate assessment
        ↓
创建新的 pending Resume Execution
```

Resume 创建不会修改来源 failed Execution，不直接启动 Runtime，也不绕过 Worker ownership。

## 2. 自动化入口

### Checkpoint / Resume targeted unit

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_workflow_execution_checkpoint.py `
  tests/unit/test_workflow_checkpoint_integration.py `
  tests/unit/test_workflow_checkpoint_recovery.py `
  tests/unit/test_workflow_execution_resume.py
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
uv run pytest -q tests/api_real/test_workflow_checkpoint_api.py -m real_api
```

该测试要求预先准备 Real API、Worker 与 PostgreSQL；不会启动、停止或重启任何服务。正式验收优先使用 Tenant Safe Real API Gate。

## 3. 服务版本前置

代码更新后必须人工重启受影响的 API Service 与 Worker Service，使进程载入最新代码；测试 Gate 禁止进行服务生命周期控制。

```powershell
# Terminal 1
uv run python run.py

# Terminal 2
uv run python run_worker.py
```

Scheduler 对本次 Checkpoint / Resume Execution 创建 Contract targeted gate 不是必需依赖；现有 Scheduler 若运行可保持不变。

## 4. 数据库前置

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期：

```text
0033_workflow_execution_resume_contract (head)
```

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

## 6. Durable Resume 创建断言

必须满足：

```text
failed Source Execution
    + worker_owner == None
    + 最新 Checkpoint 存在
    + checkpoint_reason == node.completed
    + checkpoint.execution_status == running
    + checkpoint.node_status == completed
    + 固定原 workflow_version_id
    ↓
resume:<execution_id>:checkpoint:<sequence>
    ↓
new pending Resume Execution
```

需要同时断言：

- `resume_of_execution_id == Source Execution.id`；
- `resume_checkpoint_sequence == Checkpoint.sequence`；
- `workflow_version_id` 与 Source Execution 完全一致；
- Source Execution 仍为 `failed`；
- 重复调用同一 Source + Checkpoint 返回同一 Resume Execution；
- Resume 创建不写 Worker owner / lease；
- Resume 创建不调用 `WorkflowRuntime`；
- Resume Execution 的 `input_data` 来自 Checkpoint `state_data`。

## 7. Worker claim 边界

Resume Execution 创建后必须仍然是普通 `pending` Execution，由 Worker 的标准 claim / lease / ownership fencing 路径处理。禁止 Resume Service 直接取得 owner 或调用 Runtime。

## 8. 当前禁止验收能力

当前禁止：

- Source failed → pending 原地复活；
- Source failed → running 原地复活；
- 绕过 Worker ownership；
- `resume_from_latest_checkpoint()` 内直接调用 WorkflowRuntime；
- Runtime 自动跳过 Checkpoint 前已完成 Node；
- HTTP `/resume`；
- automatic resume。

## 9. Real API / Backend Gate

真实验收仍必须执行：

```text
Source Baseline
    ↓
Backend targeted / regression
    ↓
Migration head
    ↓
Tenant Safe Real API
    ↓
Scheduler / Worker recovery acceptance（既有能力不回归时执行）
```

所有 Gate 均不得自动启动、停止或重启 API、Scheduler、Worker。

## 10. 当前状态

Phase 2.6 本轮新增 Resume Execution 创建契约后，仍处于开发中。下一阶段重点为 Resume Execution 的真实 PostgreSQL persistence、Worker claim/fencing 以及 Runtime 从 Checkpoint 后继续执行的确定性入口；完成前不标记 Phase 2.6 Closure。
