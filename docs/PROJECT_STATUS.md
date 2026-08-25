# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发并已有本地 Acceptance 结果；当前继续推进 Frontend API/UI 与 Browser E2E 验收。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前最新提交为 `712df24`，在 Scheduler 真实服务 restart recovery 验收基础上新增 Frontend Scheduler 持久化状态展示，复用既有正式 Scheduler API Contract；未新增第二套 Scheduler、Repository、slot key 或 Execution 实现。

开发者此前本地实际结果：

```text
02_run_scheduler_restart_acceptance.ps1：1 passed
01_run_real_api_tests_tenant_safe.ps1：36 passed
05_scheduler_lifecycle_gate.ps1：2 passed
04_scheduler_tenant_misfire_gate.ps1：22 misfire unit tests、3 PostgreSQL tenant integration、6 API Contract、397 Backend regression 均通过；3 skipped，36 deselected
```

以上 Backend 结果来自开发者本地实际执行反馈。当前新增 Frontend Scheduler UI 测试与 Browser E2E 变更尚未由开发者本地执行，因此不得提前宣称 Frontend Gate 或 Browser E2E 已通过。

## 本轮工程变更

- `frontend/src/api/workflows.ts`：增加 `SchedulerStatus` 类型，并通过正式 `GET /workflows/{workflow_id}/triggers/{trigger_id}/schedule` Contract 查询持久化状态；补充中文函数文档，明确参数与返回值。
- `frontend/src/views/workflow-triggers/index.vue`：在 Scheduled Trigger 上提供“调度状态”入口，展示持久化 Scheduler 状态、misfire、catch-up、next/last run、lease 与最近 Execution；不在前端复制 Scheduler 计算规则。
- `frontend/tests/api/workflows.test.ts`：验证 Scheduler 状态 API 路径与 Contract。
- `frontend/tests/views/WorkflowTriggers.test.ts`：验证 Scheduler 状态加载及 Trigger 状态变更后的状态清理。
- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：扩展真实 Browser 链路，验证真实 HTTP Scheduler 状态 Contract 与页面展示。
- 未新增并行 Scheduler / Repository / Provider / Execution 实现；Frontend 只消费 Backend 正式 Contract。

## 测试入口纠正

Frontend 与 Backend Gate 必须在各自工作目录执行。开发者若在 `backend` 目录执行 `npm test` / `npm run build`，由于 `backend/package.json` 不存在而失败属于工作目录错误，并不代表 Frontend Gate 失败。

Frontend Release / Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

其中脚本自动执行：

```text
npm test
    ↓
npm run build
```

## Phase 2.4 下一任务

```text
Frontend Vitest + production build
      ↓
Browser / Frontend-Backend Scheduler E2E
      ↓
Backend default regression + Tenant Safe Real API Gate（再次确认）
      ↓
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
      ↓
Phase 2.4 Passed 评估
```

当前不标记 Phase 2.4 Passed，直到 Frontend 与对应 Browser E2E 的本地实际结果完成记录。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果。
