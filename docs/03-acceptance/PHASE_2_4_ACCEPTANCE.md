# Phase 2.4 Durable Scheduler Acceptance

> 当前状态：**Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire integration、API/Scheduler 进程解耦已完成开发；Frontend Regression 与 Workflow Trigger Browser E2E 上轮已由开发者本地实际通过；服务化拆分后的 Backend / Real API / Restart Acceptance 需要重新执行。**
> 验收基线：`main`
> 评估日期：2026-08-25

## 1. 当前 Gate

| 项目 | 状态 |
|---|---|
| Contract / timezone / DST | 本地 Gate 已通过：13 passed（上一轮） |
| Scheduler 持久化模型 | 本地 Migration Gate 已通过（上一轮） |
| Alembic `0028_durable_scheduler_persistence` | 本地 `current` 为 head（上一轮） |
| 原子 lease claim / release | PostgreSQL Repository integration 已通过（上一轮） |
| schedule slot 幂等 claim | PostgreSQL Repository integration 已覆盖（上一轮） |
| WorkflowExecution 绑定 | Runtime Gate 已覆盖（上一轮） |
| Tenant / Organization scope | Repository lease/slot 与状态查询 tenant isolation 已覆盖 |
| Scheduler Runtime persistence 闭环 | 本地 Gate 已通过：4 passed（上一轮） |
| Scheduler API Contract / 状态可观测性 | 本地 Gate 已通过：6 passed（上一轮） |
| Misfire policy Runtime integration | 已完成开发，待最终汇总验收 |
| API / Scheduler Service 进程解耦 | **已实现，新增单元 Gate 待本轮执行** |
| Scheduler Dispatch / Recovery Scan 生命周期监督 | **已实现，新增单元测试待本轮执行** |
| Frontend Regression Gate | 上轮开发者本地实际通过：79 passed，production build 通过；服务化后需按范围重新确认 |
| Workflow Trigger Browser E2E | 上轮开发者本地实际通过：1 passed；服务化后需按范围重新确认 |
| Organization Browser E2E | 上轮结果需按本轮范围重新确认 |
| Model Provider Browser E2E | 上轮结果需按本轮范围重新确认 |
| Backend default regression | **服务化后待重新执行** |
| Tenant Safe Real API acceptance | **服务化后待重新执行** |
| Scheduler Restart Acceptance | **服务化后待重新执行** |

## 2. API / Scheduler 服务化 Acceptance

本轮完成的进程边界：

```text
API Service
    backend/run.py
    → app.main:app
    → HTTP / Auth / API Router
    → 不创建 Scheduler

Scheduler Service
    backend/run_scheduler.py
    → app.entrypoints.scheduler
    → ScheduledTriggerScheduler + WorkflowRecoveryScheduler
    → 不注册 HTTP Router
```

正式设计见 `docs/00-architecture/SERVICE_RUNTIME_ARCHITECTURE.md`。

### 固定服务身份

服务角色由启动入口唯一确定，不通过配置开关二选一：

```text
run.py
    → 必然是 API Service

run_scheduler.py
    → 必然是 Scheduler Service
```

项目不使用 `SCHEDULER_ENABLED=false` 区分 API / Scheduler，也不提供“启动 Scheduler 脚本但通过配置关闭 Scheduler”的双模式。若部署环境不需要 Scheduler，应直接不启动 `run_scheduler.py`。

验收要求：

1. API `/health` 返回 `service=api`；
2. API 进程启动不产生 Scheduler 后台 task；
3. Scheduler 入口复用唯一 `ScheduledTriggerScheduler` 与 `WorkflowRecoveryScheduler`；
4. Scheduler Service 不依赖 `SCHEDULER_ENABLED` 或同类角色开关；
5. API 与 Scheduler 的启动脚本互不调用对方；
6. 不改变现有 API Contract、数据库模型、tenant isolation、slot/idempotency 与 misfire 规则；
7. Worker Service 当前不创建空壳实现。

## 3. 自动化验证入口

服务职责边界单元测试：

```powershell
cd backend
uv run pytest -q tests/unit/test_service_entrypoints.py
```

Backend 完整 Regression：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Tenant Safe Real API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Scheduler Restart Acceptance：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

Frontend Regression：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Workflow Trigger Browser E2E：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

## 4. 启动联调流程

### Terminal A — API Service

```powershell
cd backend
uv run python run.py
```

验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

期望响应包含：

```json
{"status":"ok","service":"api"}
```

### Terminal B — Scheduler Service

确认本地 PostgreSQL 已启动并完成：

```powershell
cd backend
uv run alembic upgrade head
```

然后：

```powershell
uv run python run_scheduler.py
```

Scheduler Service 不提供 HTTP 入口；其运行证据来自 PostgreSQL Scheduler 状态、WorkflowExecution、Audit/Trace 与对应 Acceptance。

### 关闭顺序

```text
先停止 Scheduler Service
    ↓
再停止 API Service
```

这样可以在联调时明确区分 API 生命周期与调度生命周期。

## 5. 历史失败与修复链路

此前 Browser / Real API 阶段曾暴露 Workflow Trigger Contract、Scheduler UI 初始化竞争、持久化 Config 漂移、Scheduler Restart 端口冲突以及历史空节点 Workflow Definition 兼容问题。相关修复均已经进入 main，并分别记录在对应 Error / Phase 文档。

本轮新增架构风险是 API 与 Scheduler 生命周期耦合：原 API `lifespan` 创建 Scheduler 会让 API 多实例天然形成多个 Scheduler 进程。本轮通过独立 `run_scheduler.py` 消除该进程职责耦合，但不改变已有 PostgreSQL lease / slot 的多实例保护机制。

本轮进一步收口 Scheduler Service 内部两个长期循环的生命周期：Recovery Scan 不得在 Dispatch 仍存活时静默失效；任一循环异常都必须让完整 Scheduler Service 失败收敛。

## 6. Worker Service 范围控制

Worker Service 当前仅作为架构扩展方向，不作为 Phase 2.4 的实现项。未定义 Queue/Broker、Task Contract、retry、DLQ、cancellation 与 worker lease 前，禁止创建 Worker 空壳并声称已完成服务化。

## 7. 当前结论

**Phase 2.4 尚不能标记 Passed。**

本轮 Scheduler Service 双循环生命周期监督已经实现，并补充对应 Unit Test；由于当前按主线策略暂停完整 Gate，Unit Test 未在当前环境实际执行，因此不得记录 PASS。Backend Regression、Tenant Safe Real API、Scheduler Restart Acceptance、Frontend / Browser Gate 继续待开发者后续集中执行。
