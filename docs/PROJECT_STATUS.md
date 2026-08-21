# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- 当前阶段：**Phase 1.7 Workflow Trigger Expansion / Scheduling Contract**
- 当前任务：**Phase 1.7-D Browser / Frontend-Backend E2E Scheduling Contract**
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
| Phase 1.7-C | **已完成并关闭** | Schedule Governance Frontend API/UI Contract 完成；本地 Frontend Gate 全部通过 |
| Phase 1.7-D | **已启动** | Browser / Frontend-Backend E2E Scheduling Contract 已定义，正在扩展现有 Browser Trigger E2E |

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

## 4. Phase 1.7-C 完成收口

Phase 1.7-C 已按既有 Backend Contract 完成前端 Schedule Governance Integration，未新增 Backend API、migration 或 Scheduler runtime implementation。

### 已完成

- `WorkflowTrigger.trigger_type` 支持 `manual | scheduled`。
- 新增 `ScheduledTriggerConfig` 前端类型。
- Scheduled Trigger 默认配置 `timezone=UTC, interval_seconds=60`。
- 创建前校验 timezone 非空、interval_seconds 为正整数。
- Trigger inventory 展示 schedule contract。
- Scheduled Trigger 不显示 Manual Invoke。
- enable / disable / delete 沿用现有 Trigger API。
- Tenant 不由前端提交。
- 前端未实现 next-run、slot、recovery、lease、worker coordination。
- `WorkflowTriggers.test.ts` 覆盖 scheduled inventory / contract / create / invalid interval，以及 manual CRUD / invoke 回归。

### 测试结果

开发者已反馈本地 Frontend 测试全部通过，因此 Phase 1.7-C 收口采用实际结果：

```text
npm test
51 passed

npm run build
PASS

01_frontend_regression_gate.ps1
PASS
```

此前 Backend 独立 Gate 最近实际结果仍为：

```text
uv run pytest -q
245 passed, 17 deselected

uv run alembic upgrade head
success

01_run_real_api_tests.ps1
17 passed
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

### 测试桩修正

Frontend Schedule Contract 的两项失败来自 `el-table-column` 测试 stub 未保留 `prop` 与 scoped-slot rendering 语义；未修改生产 Scheduler 或 Governance UI 以适配错误 stub。测试 stub 已修正并提交 main。

## 5. Phase 1.7-C 工程清理

已清理确认被正式 Backend Release Gate 替代且无引用的旧 regression wrapper：

```text
backend/scripts/test/regression/01_backend_regression.ps1
backend/scripts/test/regression/README.md
```

同时移除空的 `backend/README.md`，避免与根 README / `docs/DEVELOPMENT.md` 形成重复入口。

保留仍有明确职责的脚本域：

```text
backend/scripts/dev/
backend/scripts/evaluation/
backend/scripts/migration/
backend/scripts/test/api-real/
backend/scripts/test/integration/
backend/scripts/test/phase/
backend/scripts/test/release/
```

## 6. Phase 1.7-D 实施范围

Phase 1.7-D 继续复用已有 Browser E2E 测试基础设施，不新建重复 Gate。

目标是把既有 Manual Trigger Browser Contract 扩展为 Scheduled Trigger Browser Contract，覆盖：

1. Browser 登录与真实 Workflow fixture；
2. Schedule Governance 页面；
3. Scheduled Trigger 创建；
4. `timezone + interval_seconds` UI contract；
5. Scheduled Trigger inventory；
6. Scheduled Trigger 不显示 Manual Invoke；
7. enable / disable / delete lifecycle；
8. 通过真实 HTTP API 检查 Trigger persistence；
9. 后续补充可控 scheduler interval 与 Workflow Execution runtime observation。

新增阶段文档：

```text
docs/20-phase-1.7-d-browser-frontend-backend-e2e.md
```

Browser E2E 仍不重复执行 Backend pytest、migration、Real API 全量 Gate 或 Frontend regression。

## 7. Phase 1.7-D 本地测试流程

### 1. Frontend regression

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### 2. Backend regression / migration / Real API

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### 3. Browser E2E

启动 Backend 与 Frontend 后：

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

本阶段 Browser E2E 的目标结果不是复制其他 Gate，而是验证真实 Browser → Vue → HTTP → Trigger persistence → Scheduler / Execution 的跨层契约。

## 8. 下一步

```text
Phase 1.7-C
  C-01 API Type Contract          ← 完成
  C-02 Schedule Governance UI     ← 完成
  C-03 Runtime Boundary           ← 完成
  C-04 Frontend Tests              ← 完成
        ↓
Phase 1.7-C 关闭
        ↓
Phase 1.7-D Browser / Frontend-Backend E2E
  D-01 Browser Schedule Governance
  D-02 Trigger Lifecycle
  D-03 Scheduler / Execution Boundary
  D-04 Regression Boundaries
        ↓
Phase 1.7 最终验收 / 关闭评估
```

本状态文件只记录已经确认的实际结果；Phase 1.7-D 的 Browser Gate 在实际执行前不预先宣称通过。
