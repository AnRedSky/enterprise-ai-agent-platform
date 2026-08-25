# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；上一轮独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**代码实现完成；本轮 Backend / Migration / Real Acceptance 待开发者本地执行。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前主线已经完成两级服务化边界：

```text
API Service
    run.py

Scheduler Service
    run_scheduler.py

Worker Service
    run_worker.py
```

服务角色由启动入口固定确定，不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 等配置开关切换角色。

## 当前执行链

```text
API Service
    ↓ HTTP
Workflow / Trigger Domain
    ↓
Scheduler Service
    ├── schedule
    ├── lease
    ├── slot
    ├── misfire
    └── create pending WorkflowExecution
              ↓ PostgreSQL
Worker Service
    ├── claim pending Execution
    ├── worker lease
    └── WorkflowExecutionService.run()
              ↓
WorkflowRuntime
```

核心职责已经明确：

> **Scheduler 负责“什么时候执行”，Worker 负责“执行什么”。**

## 本轮 Scheduler → Worker 变更

### Scheduler

`WorkflowTriggerService.invoke_scheduled()` 不再直接调用 `WorkflowExecutionService.run()`。

现在 Scheduled Trigger 只负责：

1. 校验 Trigger / Published Version；
2. 计算并接收 Scheduler slot metadata；
3. 通过 idempotency claim 创建 `pending WorkflowExecution`；
4. 写入 Audit / Trace；
5. 返回待执行任务。

Scheduler Runtime 随后绑定 slot 与 Execution 并推进持久化 schedule。

### Worker

新增：

```text
backend/app/services/workflow_worker/
├── __init__.py
└── runtime.py

backend/app/entrypoints/worker.py
backend/run_worker.py
```

Worker：

- 使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 认领 pending Execution；
- 写入 `worker_owner / worker_lease_expires_at / worker_attempt`；
- 复用唯一 `WorkflowExecutionService`；
- 复用唯一 `WorkflowRuntime`；
- 不实现 Scheduler slot / misfire / Trigger / Provider / Runtime 第二套规则；
- 默认并发 4、claim lease 60s、poll 1s。

### Database

新增 Migration：

```text
0029_workflow_worker_lease
```

新增字段：

```text
workflow_executions.worker_owner
workflow_executions.worker_lease_expires_at
workflow_executions.worker_attempt
```

并增加 Worker claim 索引与 lease 成对约束。

## Legacy Definition 兼容

历史 Scheduled Execution 仍保留受控的空 nodes 兼容，但 Worker 不扩大兼容范围：

```text
scheduled_slot 存在 → 使用已有 Scheduler legacy compatibility
普通 Manual Execution → 严格 Definition 校验
```

不新增第二套 Definition validator。

## 当前服务架构

```text
API Service
    backend/run.py
    └── FastAPI / HTTP / Auth / API Router

Scheduler Service
    backend/run_scheduler.py
    └── ScheduledTriggerScheduler
        ├── PostgreSQL lease
        ├── schedule slot
        ├── misfire
        └── pending WorkflowExecution dispatch

Worker Service
    backend/run_worker.py
    └── WorkflowWorker
        ├── PostgreSQL pending claim
        ├── worker lease
        └── WorkflowExecutionService → WorkflowRuntime
```

API、Scheduler、Worker 三者共享正式 Domain / Infrastructure，但生命周期完全独立。

## 当前 Gate 状态

本轮代码变更完成后，必须重新执行：

```text
① Worker Unit
② Backend default regression
③ Database migration/head
④ Scheduler + Worker Real Acceptance
⑤ Frontend Regression（受范围影响时）
⑥ Workflow Trigger Browser E2E（受范围影响时）
```

本文件不预填本轮测试通过结果。

上一轮实际结果仍为：

```text
Backend default regression: 403 passed, 3 skipped, 36 deselected
Tenant Safe Real API Gate: 35 passed
Scheduler independent restart acceptance: 1 passed
Frontend Regression: 79 passed + production build
Workflow Trigger Browser E2E: 1 passed
```

以上结果属于上一轮服务化提交，不能作为 Phase 2.5 本轮代码变更后的验收结果。

## 本地启动

### API Service

```powershell
cd backend
uv run python run.py
```

### Scheduler Service

```powershell
cd backend
uv run python run_scheduler.py
```

### Worker Service

```powershell
cd backend
uv run python run_worker.py
```

如果需要完整 Scheduled Workflow 执行链，本地必须同时运行 Scheduler 与 Worker；API 是否运行只取决于是否需要 HTTP 管理入口。

## 当前禁止事项

- 不恢复 API 内嵌 Scheduler；
- 不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 区分服务角色；
- 不让 Scheduler 直接执行 Workflow Runtime；
- 不创建第二套 Execution Service / Runtime / Provider；
- 不通过 JSON fixture 替代真实 PostgreSQL Task Contract；
- 不通过 Mock Runtime 作为 Real Acceptance；
- 不在本阶段偷偷加入 running Execution 自动 resume；
- 不创建 MQ/Kafka/Celery 等 Broker 作为当前阶段必要依赖；
- 不创建功能分支，所有开发直接基于并提交 `main`。

## 文档记录

本轮同步维护：

- `docs/00-architecture/SERVICE_RUNTIME_ARCHITECTURE.md`
- `docs/02-phases/PHASE_2_5.md`
- `docs/03-acceptance/PHASE_2_5_ACCEPTANCE.md`
- `docs/PROJECT_STATUS.md`
