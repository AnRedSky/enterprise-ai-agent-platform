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
- 当前子任务：**D-03 Scheduler / Execution Boundary**
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
| Phase 1.7-D | **进行中** | Browser / Frontend-Backend E2E Scheduling Contract 已建立；D-01/D-02 基础链路已有测试，当前推进 D-03 Scheduler / Execution Boundary |

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

已实现/正在推进：

- Browser 登录与真实 Workflow fixture；
- Schedule Governance 页面；
- Scheduled Trigger 创建；
- `timezone + interval_seconds` UI contract；
- Scheduled Trigger inventory；
- Scheduled Trigger 不显示 Manual Invoke；
- enable / disable / delete lifecycle；
- 通过真实 HTTP API 检查 Trigger persistence；
- D-03 新增短 interval 的真实 application scheduler observation：通过 `/runtime/executions` 检查 scheduler 产生的 deterministic `scheduled:{trigger_id}:{slot}` Execution。

D-03 测试保持边界：

- 前端不计算 next-run；
- 前端不实现 scheduler polling；
- 不修改生产 Scheduler 语义以适配 E2E；
- 使用独立测试 Workflow / Trigger；
- 使用 5 秒短 interval 作为真实 scheduler observation 的受控测试数据。

### 最近 E2E 修正

已修正两类实际测试契约问题：

1. Element Plus Scheduled 类型下拉采用键盘选择，避免 teleported dropdown 动画造成 `locator.click` 不稳定。
2. Config JSON 采用语义 JSON 断言，不要求 UI textarea 必须保持 minified 格式。
3. Trigger list 的真实 Backend API 返回数组；E2E persistence assertion 现兼容真实数组响应，并保持对 `items` 包装响应的防御性读取，但生产 API contract 仍以 Backend 实现为准。

当前 main 最新修复提交：

```text
d84df68 fix(e2e): align trigger persistence assertion with API response contract
7236570 feat(e2e): cover scheduled trigger execution boundary
```

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

D-03 需要 Backend scheduler 实际启用；E2E 不在脚本中重复启动或修改生产 scheduler。

### 当前验收状态

本轮 `d84df68` / `7236570` 的代码已提交 main，但尚未把用户本地最新 Browser Gate 结果预先标记为通过。必须以本地实际执行结果作为 D-03 验收依据。

## 8. 下一步

```text
Phase 1.7-D
  D-01 Browser Schedule Governance     ← 已实现
  D-02 Trigger Lifecycle               ← 已实现
  D-03 Scheduler / Execution Boundary  ← 当前
  D-04 Regression Boundaries           ← 待 D-03 实际 Gate 通过后收口
        ↓
Phase 1.7 最终验收 / 关闭评估
```

本状态文件只记录已经确认的实际结果；Phase 1.7-D Browser Gate 与 D-03 Runtime observation 在实际执行前不预先宣称通过。
