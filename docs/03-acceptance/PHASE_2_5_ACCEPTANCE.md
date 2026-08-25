# Phase 2.5 — Scheduler → Worker 执行解耦 Acceptance

## 1. 验收目标

验证 Scheduler 与 Workflow Runtime 已经形成真实进程边界：

```text
Scheduler Service
    ↓ PostgreSQL pending Execution
Worker Service
    ↓ WorkflowExecutionService
WorkflowRuntime
```

不能通过同一进程内调用、Mock Runtime 或 JSON fixture 替代。

## 2. 自动化入口

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

该脚本必须负责：

1. 启动临时 API Service，仅用于 tenant-safe fixture bootstrap；
2. 启动独立 Scheduler Service；
3. 停止 Scheduler；
4. 修改真实 PostgreSQL 的 schedule 状态，制造历史 slot；
5. 启动独立 Scheduler Service；
6. 启动独立 Worker Service；
7. 通过真实 PostgreSQL 等待 WorkflowExecution 完成；
8. 校验 Audit / Trace / tenant / workflow / execution 关联；
9. 校验同一 idempotency key 不产生重复 Execution；
10. 清理测试 Workflow。

## 3. 本地服务准备

自动化 Acceptance 不要求开发者手工修改代码或测试文件。

脚本会自己启动：

```text
临时 API Service
Scheduler Service
Worker Service
```

因此开发者不需要预先启动三个服务；如果本地已经运行 `run.py`、`run_scheduler.py` 或 `run_worker.py`，Acceptance 脚本应先提示并要求停止冲突进程。

## 4. 独立手工运行方式

如需要观察真实服务日志，可分别打开三个 PowerShell：

### PowerShell 1 — API

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python run.py
```

### PowerShell 2 — Scheduler

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python run_scheduler.py
```

### PowerShell 3 — Worker

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python run_worker.py
```

服务身份固定：

```text
run.py           → API Service
run_scheduler.py → Scheduler Service
run_worker.py    → Worker Service
```

不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 进行角色切换。

## 5. Backend 回归

```powershell
cd backend
uv run pytest -q
```

## 6. Migration 验证

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

预期：

```text
0029_workflow_worker_lease
```

## 7. Worker 定向测试

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker.py
```

## 8. 验收断言

必须满足：

```text
[PASS] Scheduler Service 可以独立启动
[PASS] Scheduler 可以创建 WorkflowSchedule
[PASS] Scheduler 不直接执行 WorkflowRuntime
[PASS] Scheduler 可以创建 pending WorkflowExecution
[PASS] Worker Service 可以独立启动
[PASS] Worker 可以 claim pending Execution
[PASS] Worker 使用唯一 WorkflowExecutionService
[PASS] WorkflowRuntime 最终完成 Execution
[PASS] Scheduler restart 后历史 slot 可以恢复
[PASS] slot / Execution idempotency 唯一
[PASS] AuditLog tenant/workflow/execution 关联正确
[PASS] WorkflowTraceEvent tenant/workflow/execution 关联正确
```

## 9. 禁止验收方式

以下方式不能作为本阶段通过依据：

- 只执行 Unit Test，不执行真实 PostgreSQL；
- Scheduler 进程内部直接调用 Runtime；
- Worker 使用 Mock Runtime 证明真实执行成功；
- 用 JSON fixture 代替 WorkflowExecution；
- 手工修改生产代码让测试通过；
- 使用 GitHub Actions 结果替代本地 Gate。

## 10. 当前状态

代码已提交到 `main` 后，必须由开发者在本地执行上述 Gate。未收到实际执行结果前，本 Acceptance 不标记为 Passed。
