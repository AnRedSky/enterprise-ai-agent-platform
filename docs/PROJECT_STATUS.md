# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- 当前阶段：**Phase 1.7 Workflow Trigger Expansion / Scheduling Contract**
- 当前任务：**Phase 1.7-C Schedule Governance / Frontend Integration**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5 | **已完成** | Workflow / Governance A～G 全部完成；Circuit Breaker 最终验收通过 |
| Phase 1.6-A | **已完成** | Workflow Trigger Backend Contract；Backend Domain / API / Migration / Contract / Real API 两道 Gate 通过 |
| Phase 1.6-B | **已完成** | Frontend API Type / Vitest / Workflow Trigger Governance UI；Frontend Regression、Trigger Real HTTP、UI 手动验收通过 |
| Phase 1.6-C | **已完成** | Browser / Frontend-Backend E2E 第三独立测试层建立并通过；最终 Browser E2E 1 passed |
| Phase 1.6 | **已正式关闭** | A～C 全部完成，三层 Gate 与实际联调完成 |
| Phase 1.7-A | **基线审计完成** | Scheduled Trigger Contract、Scheduler Runtime、bounded recovery、multi-worker slot convergence 已存在于最新 main；不重复实现 |
| Phase 1.7-B | **核心 Persistence Gate 已通过；专项 Runtime failure 待完成** | Scheduled current/recovery persistence、idempotency、Real API lifecycle 已完成并通过；Runtime failure persistence 仍需专项真实失败 Workflow 验收 |
| Phase 1.7-C | **开发中** | Schedule Governance Frontend API/UI Contract 已开始实施 |

## 3. Phase 1.7-A/B 基线结论

当前 main 已包含：

```text
Scheduled Trigger Contract
        ↓
FastAPI lifespan Scheduler
        ↓
interval slot
        ↓
deterministic idempotency key
        ↓
bounded recovery slots
        ↓
WorkflowExecutionService.create()
        ↓
workflow_executions persistence
        ↓
WorkflowExecutionService.run()
        ↓
completed / failed Execution
```

Scheduler 使用 PostgreSQL transaction-scoped advisory lock 配合既有 `(tenant_id, idempotency_key)` unique constraint 作为同 slot 多 worker 的数据库收敛边界。本阶段不增加并发旁路方案。

Phase 1.7-B 已完成并验证：

- current scheduled slot persistence；
- recovery slot persistence；
- deterministic idempotency key；
- duplicate tick / scheduler restart 不重复产生同 slot Execution；
- Real API 测试进程 AsyncEngine event-loop 生命周期治理；
- recovery 测试按 per-trigger persistence contract 断言，而非错误解释 global scheduler counters。

## 4. 最近实际验收结果

开发者最近一次反馈：

```text
Backend pytest:
245 passed, 17 deselected in 4.81s

Migration:
uv run alembic upgrade head -> success

Real API Gate:
17 passed in 33.44s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

直接执行：

```text
uv run pytest -q tests/api_real/test_scheduled_trigger_api.py -m real_api
```

得到 3 个 `TRIGGER_WORKFLOW_ID is required`，因为该命令绕过统一 Real API bootstrap；不作为 Gate 失败结论。Real API 必须使用统一入口脚本准备上下文。

## 5. Phase 1.7-C 基线审计

现有 Frontend 已有 `Workflow Trigger Governance` 页面、Trigger CRUD、enable/disable、manual invoke 和 API client，但 `WorkflowTrigger.trigger_type` 当前只允许 `manual`，因此不能完整消费后端已经存在的 scheduled Trigger Contract。

后端已提供统一 Trigger API：

```text
GET    /workflows/{workflow_id}/triggers
POST   /workflows/{workflow_id}/triggers
GET    /workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /workflows/{workflow_id}/triggers/{trigger_id}
DELETE /workflows/{workflow_id}/triggers/{trigger_id}
POST   /workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

因此 1.7-C 不新增 Backend API、不新增 migration、不重复实现 Scheduler。

## 6. Phase 1.7-C 已实施代码范围

### API Types

- `WorkflowTrigger.trigger_type` 扩展为 `manual | scheduled`。
- 新增 `ScheduledTriggerConfig` 类型。
- Trigger create/update client 不再把类型锁死为 manual。

### Schedule Governance UI

- Trigger 创建支持 `manual / scheduled`。
- scheduled 默认配置为 `timezone=UTC, interval_seconds=60`。
- 前端仅执行最小输入校验，不替代 Backend Contract。
- 列表展示 scheduled Trigger 的 timezone / interval。
- scheduled Trigger 不显示 manual Invoke 操作。
- Tenant 不由前端提交。
- 不实现 next-run、slot、recovery、lease、worker 状态等后端运行时逻辑。

### Frontend tests

`frontend/tests/views/WorkflowTriggers.test.ts` 增加：

- scheduled inventory；
- schedule contract 展示；
- scheduled create；
- invalid interval 拦截；
- manual CRUD / invoke 回归。

## 7. 工程清理

本轮清理已确认被正式 Backend Release Gate 替代且无引用的旧 regression wrapper：

```text
backend/scripts/test/regression/01_backend_regression.ps1
backend/scripts/test/regression/README.md
```

同时移除空的 `backend/README.md`，避免与根 README / `docs/DEVELOPMENT.md` 形成重复入口。

保留以下仍有明确职责的脚本域：

```text
backend/scripts/dev/
backend/scripts/evaluation/
backend/scripts/migration/
backend/scripts/test/api-real/
backend/scripts/test/integration/
backend/scripts/test/phase/
backend/scripts/test/release/
```

## 8. Phase 1.7-C 测试步骤

开发者在拉取本轮 main 后执行：

### Frontend

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### Backend 独立 Gate

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### Browser E2E

Phase 1.7-D 再加入 Schedule 用户链路；C 阶段不复制 Browser Gate。

本轮代码提交前未由开发者执行上述 Frontend 命令，因此这里不预填测试通过结果。

## 9. 下一步

```text
Phase 1.7-C
  C-01 API Type Contract          ← 已实施
  C-02 Schedule Governance UI     ← 已实施
  C-03 Runtime Boundary           ← 已实施
  C-04 Frontend Tests              ← 已实施
        ↓
本地 Frontend Gate 验收
        ↓
Phase 1.7-D Real HTTP + Browser E2E scheduling contract
        ↓
最终关闭 Phase 1.7
```

本状态文件只记录已经确认的实际结果，不预先宣称未执行的 Gate 通过。
