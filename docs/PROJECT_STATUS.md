# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发并已有本地 Acceptance 结果；Frontend / Browser E2E 仍在验收。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 已完成 Workflow Trigger Browser E2E 的 API Client、Auth、Workflow Version、正式路由、Browser Session、Element Plus Select、Trigger 持久化实体等待等 Contract 对齐。开发者最新本地反馈中，Frontend Regression Gate 已实际通过 79 tests，production build 也已通过；Workflow Trigger Browser E2E 已进入正式 `/workflows/triggers` 页面、完成 Trigger 类型选择并成功创建 Trigger。随后测试在 Scheduler UI 首次查询仍处于异步初始化窗口时，直接读取 `scheduler-timezone`，导致元素尚未渲染而失败。

本轮继续修复该真实 E2E 时序问题：测试先通过真实 HTTP 确认 PostgreSQL Scheduler 状态已经持久化，再在生产 UI 未显示状态字段时点击 Scheduler 卡片的正式“刷新”入口，最后继续使用真实 DOM test hook 验证 `timezone / misfire_policy / catch_up_limit`。不使用固定 sleep、不构造测试数据、不降低业务断言。

**当前 Browser Gate 尚未由开发者重新执行，因此不得标记为通过。**

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：
  - 修复 Scheduler Backend 已持久化而 Frontend 首次查询尚未刷新时的 UI 时序竞争；
  - 先完成真实 HTTP Scheduler Contract 轮询，再使用生产 UI 的“刷新”操作同步页面状态；
  - 最终仍验证真实 `scheduler-timezone`、`scheduler-misfire-policy`、`scheduler-catch-up-limit`。
- `docs/04-errors/2026-08-25-browser-e2e-scheduler-ui-race.md`：
  - 记录 Scheduler UI 初始化时序竞争的现象、根因、修复边界与本地验收要求。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：已完成真实 Trigger 创建并进入 Scheduler 状态验收；本轮因 UI 初始化时序竞争失败，测试已修复，等待开发者重新执行
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
修复 Browser E2E 测试实现的 API Client / Auth / Version / Route / Browser Session / UI Select / Persistence Poll / Scheduler UI Sync Contract 漂移
      ↓
Browser Scheduler Gate 重新执行
      ↓
Organization Browser E2E / Model Provider Browser E2E 状态再次确认
      ↓
Backend default regression + Tenant Safe Real API Gate（再次确认）
      ↓
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
      ↓
Phase 2.4 Passed 评估
```

当前不标记 Phase 2.4 Passed。必须等待本轮 Workflow Trigger Browser Gate 修复后的本地实际结果，并完成后续 Backend Gate / Real API / Acceptance 汇总。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；测试应匹配真实生产 UI 语义并使用稳定 test hooks；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果。
