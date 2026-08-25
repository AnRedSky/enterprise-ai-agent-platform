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

产品级 Worker 执行架构记录：

```text
docs/00-architecture/WORKFLOW_WORKER_EXECUTION_ARCHITECTURE.md
```

## 2. 自动化入口

Tenant Safe Real API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Scheduler / Worker Recovery Acceptance：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

Backend Release Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

上述 Gate 都遵循项目开发准则：测试脚本不启动、停止或重启 API、Scheduler、Worker；脚本只验证已经存在的服务与真实 PostgreSQL 链路，并在前置服务缺失时明确失败。

## 3. 本地服务准备

自动化 Gate 不要求开发者手工修改测试文件或生产代码，但需要开发者预先运行所涉及的服务。

### Real API Gate

需要：

```text
API Service + Worker Service + PostgreSQL
```

### Scheduler / Worker Recovery Acceptance

需要：

```text
Scheduler Service + Worker Service + PostgreSQL
```

### 服务启动命令

分别打开 PowerShell：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python run.py
```

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python run_scheduler.py
```

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

## 4. Backend 回归

```powershell
cd backend
uv run pytest -q
```

## 5. Migration 验证

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

当前 main 基线预期 Migration Head：

```text
0031_usage_provider_lifecycle
```

本阶段代码没有新增 Migration，但每次 Backend Gate 仍必须实际验证当前 head。

## 6. Worker 定向测试

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker.py
```

当前本地反馈：

```text
9 passed in 1.09s
```

## 7. Worker 执行流程验收断言

必须满足：

```text
[PASS] Scheduler Service 可以独立运行
[PASS] Scheduler 可以创建 WorkflowSchedule
[PASS] Scheduler 不直接执行 WorkflowRuntime
[PASS] Scheduler 可以创建 pending WorkflowExecution
[PASS] Worker Service 可以独立运行
[PASS] Worker 可以 claim pending Execution
[PASS] Worker 写入 worker_owner / lease / attempt
[PASS] Worker heartbeat 可以保持长任务 ownership
[PASS] Worker 使用唯一 WorkflowExecutionService
[PASS] Runtime 开始前可以恢复 pending Execution 上遗留 running Node
[PASS] WorkflowRuntime 最终完成或失败 Execution
[PASS] Scheduler restart 后历史 slot 可以恢复
[PASS] slot / Execution idempotency 唯一
[PASS] AuditLog tenant/workflow/execution 关联正确
[PASS] WorkflowTraceEvent tenant/workflow/execution 关联正确
[PASS] Worker claim 后 HTTP /run 不进入第二个 Runtime
[PASS] Node 状态机仍拒绝 running → running
```

### 7.1 Execution Idempotency 的状态语义

幂等重放的验收重点是：相同 `Idempotency-Key` 必须解析到同一个 `WorkflowExecution`，而不是要求 HTTP 重放响应永远保持 `pending`。

由于 Scheduler / Worker 已经形成独立进程边界，Worker 可以在两次 HTTP 请求之间消费该 Execution。因此真实 API 重放返回的 `status` 允许是当前持久化状态，例如：

```text
pending / running / completed / failed / cancelled
```

禁止用固定 `pending` 作为幂等契约，否则会把正常的异步执行进度误判为可靠性失败。

### 7.2 Worker ownership fencing

必须验证 Worker lease 失效后旧消费者不能继续修改同一个 Execution：

```text
Worker A claim
    ↓ worker_owner=A
lease 失效 / Worker B 接管
    ↓ worker_owner=B
Worker A 再次 transition
    ↓
409 Workflow Execution Worker ownership 已失效
    ↓
Worker A 放弃 stale consumer
```

还必须验证本轮新增的 Runtime 入口 fencing：

```text
Worker A claim
    ↓ worker_owner=A, status=pending
HTTP /run
    ↓
409 只有 pending Execution 可以 Run
    ↓
HTTP Runtime 不启动

Worker A
    ↓ worker_owner=A
WorkflowExecutionService.run(worker_owner=A)
    ↓
允许进入 Runtime
```

### 7.3 Worker recovery

当 Worker claim 后发现：

```text
Execution.status = pending
Node.status = running
```

必须先执行：

```text
running → failed
error_code = WORKER_RECOVERY_INTERRUPTED
```

然后由既有 Runtime 进入合法的：

```text
failed → running
```

禁止把 `running → running` 加入状态机，也禁止通过 reset 数据库隐藏恢复问题。

### 7.4 Real API Worker claim race

创建 Execution 后 Worker 可能先于 HTTP `/run` claim。测试必须使用：

```text
backend/tests/api_real/execution_helpers.py
run_or_observe_execution()
```

该 helper 的语义是：

1. 首先真实调用 HTTP `/run`；
2. 若直接返回预期状态，立即校验持久化结果；
3. 若返回 `409 只有 pending Execution 可以 Run`，只将其识别为合法 Worker claim 竞态；
4. 继续通过真实 HTTP 查询等待 Execution 终态；
5. 测试根据业务 Fixture 将最终持久化状态映射为有效结果；
6. 其他 409 / HTTP 状态仍然失败。

本轮 Circuit Breaker probe 测试已统一采用该 helper，避免把真实 Worker 调度时序误判为生产错误。

## 8. 禁止验收方式

以下方式不能作为本阶段通过依据：

- 只执行 Unit Test，不执行真实 PostgreSQL；
- Scheduler 进程内部直接调用 Runtime；
- Worker 使用 Mock Runtime 证明真实执行成功；
- 用 JSON fixture 代替 WorkflowExecution；
- 手工修改生产代码让测试通过；
- 使用 GitHub Actions 结果替代本地 Gate；
- 让 Gate 脚本自动启动、停止或重启本地服务；
- 通过放宽 `running → running` 消除错误日志；
- 通过降低 Worker polling 频率规避 claim 竞态。

## 9. 当前状态

代码已经进入 `main`，Worker targeted tests 已由开发者本地反馈通过；本轮 Tenant Safe Real API 曾因 Circuit Breaker probe 的合法 Worker claim 竞态失败。测试已整改为观察真实持久化结果，但在开发者重新执行 Gate 前，本 Acceptance 不标记为最终 Passed。
