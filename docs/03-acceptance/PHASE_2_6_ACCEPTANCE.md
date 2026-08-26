# Phase 2.6 — Durable Execution Checkpoint Foundation Acceptance

## 1. 验收目标

验证 WorkflowRuntime 的 Node completion 已形成真实 PostgreSQL Checkpoint 持久化边界，并验证 Durable Resume 的完整顺序恢复链路：

```text
Real HTTP Source Execution
        ↓
Worker claim / lease / ownership fencing
        ↓
Node completion
        ↓
PostgreSQL immutable Checkpoint
        ↓
Source failed
        ↓
WorkflowExecutionService.resume_from_latest_checkpoint()
        ↓
new pending Resume Execution
        ↓
Worker claim
        ↓
Source / Checkpoint / Version revalidation
        ↓
Resume Planner
        ↓
只执行 Checkpoint 之后的 Nodes
        ↓
Resume Execution 自己产生新的 Checkpoint
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
  tests/unit/test_workflow_execution_resume.py `
  tests/unit/test_workflow_resume_planner.py `
  tests/unit/test_workflow_worker.py `
  tests/unit/test_workflow_execution_worker_fencing.py `
  tests/unit/test_workflow_worker_lease_heartbeat.py
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

### Durable Resume real Worker acceptance

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\03_run_durable_resume_acceptance.ps1
```

该 Gate 只验证并使用开发者提前人工启动的 API Service 与 Worker Service，不启动、停止或重启任何 API / Scheduler / Worker 进程；测试进程内临时 Provider 仅用于模拟一次真实 503、随后 200 的外部 HTTP 调用。

## 3. 服务前置

本次 Durable Resume acceptance 依赖 API Service 与 Worker Service，必须由开发者提前手动启动。

```powershell
# Terminal 1
cd backend
uv run python run.py

# Terminal 2
cd backend
uv run python run_worker.py
```

Scheduler Service 不是本次 Resume acceptance 的直接依赖；若本地已经运行 `run_scheduler.py`，保持现状即可，Gate 不控制其生命周期。

代码更新后必须人工重启受影响服务，使 Worker / API 载入最新源码；不要依赖测试脚本自动重启。

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

## 5. Source → Checkpoint 断言

验收用例创建一个两节点顺序 Workflow：

```text
prepare(input)
    ↓
provider-call(agent)
```

临时 Provider 第一次返回 HTTP 503，因此 Source Execution 必须：

- `status == failed`；
- `worker_owner == None`；
- `prepare` 为 `completed`；
- `provider-call` 为 `failed`；
- PostgreSQL 中只有一条 Checkpoint；
- `checkpoint.sequence == 1`；
- `checkpoint.node_id == prepare`；
- `checkpoint.node_status == completed`；
- `checkpoint.state_data` 等于 `prepare` 完成时的输入状态。

## 6. Resume Execution 创建断言

测试通过正式 `WorkflowExecutionService.resume_from_latest_checkpoint()` 创建 Resume，而不是直接写表：

```text
failed Source Execution
    + worker_owner == None
    + latest Checkpoint exists
    + checkpoint_reason == node.completed
    + checkpoint.execution_status == running
    + checkpoint.node_status == completed
    + workflow_version_id unchanged
        ↓
new pending Resume Execution
```

必须同时满足：

- `resume_of_execution_id == Source Execution.id`；
- `resume_checkpoint_sequence == Checkpoint.sequence`；
- `workflow_version_id` 与 Source 完全一致；
- Source 仍保持 `failed`；
- Resume 初始状态为 `pending`；
- Resume 未获取 Worker owner / lease；
- Resume `input_data` 等于 Checkpoint `state_data`。

## 7. Worker 顺序恢复断言

创建 Resume 后，测试不调用 `/run`，而是等待已经人工启动的 Worker 按正常 pending claim 路径消费：

```text
Resume pending
    ↓
Worker claim
    ↓
Source / Checkpoint / Version revalidation
    ↓
Resume Planner
    ↓
丢弃 prepare
    ↓
只执行 provider-call
```

第二次 Provider 调用返回 HTTP 200，因此 Resume Execution 必须 `completed`。

必须同时满足：

- Resume Execution 最终 `completed`；
- Resume Execution 只存在一个 `WorkflowNodeExecution`：`provider-call=completed`；
- Resume Execution 不重新创建 `prepare` Node Execution；
- Resume Execution 产生自己的 Checkpoint，sequence 在本 Execution 内从 `1` 开始；
- Resume Checkpoint 的 `node_id == provider-call`；
- Source Execution 的 Checkpoint / Node 历史不被修改；
- Source 与 Resume 之间通过 `resume_of_execution_id + resume_checkpoint_sequence` 保留 lineage。

## 8. 并发与 ownership 边界

必须保持：

1. Source failed 后没有 active Worker ownership，才允许创建 Resume。
2. Resume 必须进入普通 pending claim；禁止 Resume Service 直接进入 Runtime。
3. Worker 对每个 Execution 使用独立数据库 Session。
4. Worker heartbeat / fencing 仍由既有 Worker lease 机制负责。
5. Source 与 Resume 绝不能同时推进同一 Node Execution。
6. 不允许通过 Resume 重新让 Source Execution 从 `failed → pending → running`。

## 9. 当前禁止验收能力

当前仍禁止：

- DAG 分支自动恢复；
- running Execution checkpoint recovery；
- Saga / compensation；
- HTTP `/resume`；
- automatic resume；
- 绕过 Worker ownership fencing；
- 将 Source / Resume 两个 Execution 的 Checkpoint sequence 合并为一个全局序列。

## 10. Gate 生命周期规则

所有 Gate 都不得自动启动、停止或重启 API、Scheduler、Worker。

```text
开发者手动启动服务
        ↓
Gate 检查服务是否存在
        ↓
Gate 执行测试
        ↓
Gate 退出
        ↓
服务继续保持开发者原有生命周期
```

## 11. 当前状态

本轮已新增真实 Durable Resume Acceptance 自动化实现；是否通过以开发者本地实际执行反馈为准。该验收通过后，下一阶段进入 Resume lineage / Resume failure-after-resume 边界，再评估 DAG 图恢复规划器。
