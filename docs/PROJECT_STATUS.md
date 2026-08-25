# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发并已有本地 Acceptance 结果；Frontend API/UI 已完成实现与问题修复，当前等待 Frontend / Browser E2E 重新执行验收。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前最新提交为 `12174be`，在 `712df24` Scheduler 持久化状态展示基础上，补充 Scheduler 状态异步初始化重试、Browser E2E 场景隔离以及独立的 Workflow Trigger / Organization / Model Provider Browser Gate。

开发者此前本地实际结果：

```text
02_run_scheduler_restart_acceptance.ps1：1 passed
01_run_real_api_tests_tenant_safe.ps1：36 passed
05_scheduler_lifecycle_gate.ps1：2 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、397 Backend regression 均通过；3 skipped，36 deselected
```

以上 Backend 结果来自开发者本地实际执行反馈。当前本轮 Frontend / Browser 修复尚未由开发者本地重新执行，因此不得提前宣称 Frontend Gate 或 Browser E2E 已通过。

## 本轮工程变更

- `frontend/src/views/workflow-triggers/index.vue`：Scheduled Trigger 查询持久化 Scheduler 状态时，仅针对 Runtime 异步初始化窗口执行有限重试，不复制 Scheduler 调度、slot 或 misfire 规则；补充中文函数文档与设计意图说明。
- `frontend/tests/views/WorkflowTriggers.test.ts`：增加“首次尚未初始化、随后返回正式 Contract”的重试测试。
- `backend/scripts/test/e2e/00_reset_browser_e2e_database.py`：增加仅供本地 Browser E2E 使用的 Organization 根聚合隔离工具，不改变生产 Organization / Tenant 约束。
- `frontend/scripts/test/e2e/00_run_isolated_test.ps1`：增加逐场景自动重置数据库并运行真实 Browser E2E 的统一入口。
- `frontend/scripts/test/e2e/01_run_workflow_trigger_e2e.ps1`：修正 Gate 范围，只执行 Scheduler Workflow Trigger Browser 场景。
- `frontend/scripts/test/e2e/02_run_organization_e2e.ps1`：逐个隔离执行 Organization Browser 场景。
- `frontend/scripts/test/e2e/03_run_model_provider_e2e.ps1`：新增独立 Model Provider/Profile Browser Gate。
- `docs/04-errors/2026-08-25-scheduler-status-async-initialization.md`：记录 Scheduler 状态 API 异步初始化窗口错误及修复。
- `docs/04-errors/2026-08-25-browser-e2e-tenant-organization-isolation.md`：记录“一 Tenant 一 Organization”导致 Browser E2E 场景互相污染的问题及隔离方案。
- 未新增第二套 Scheduler / Repository / Provider / Execution / slot key 实现；Frontend 继续只消费 Backend 正式 Scheduler API Contract。

## 测试入口纠正

Frontend 与 Backend Gate 必须在各自工作目录执行。开发者若在 `backend` 目录执行 `npm test` / `npm run build`，由于 `backend/package.json` 不存在而失败属于工作目录错误，并不代表 Frontend Gate 失败。

Frontend Release / Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Browser Scheduler Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Browser Organization Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
```

Browser Model Provider Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\03_run_model_provider_e2e.ps1
```

## Phase 2.4 下一任务

```text
Frontend Vitest + production build
      ↓
Browser Scheduler / Organization / Model Provider E2E
      ↓
Backend default regression + Tenant Safe Real API Gate（再次确认）
      ↓
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
      ↓
Phase 2.4 Passed 评估
```

当前不标记 Phase 2.4 Passed，直到上述 Frontend 与对应 Browser E2E 的本地实际结果完成记录。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果。