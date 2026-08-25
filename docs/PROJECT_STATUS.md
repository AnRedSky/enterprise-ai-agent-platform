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

当前远端 `main` 已完成 Workflow Trigger Browser E2E 的 API Client、Auth、Workflow Version、正式路由、Browser Session、Element Plus Select Contract 对齐。最新开发者本地反馈显示 Frontend Regression Gate 已实际通过 79 tests，production build 也已通过；Browser E2E 已进入正式 `/workflows/triggers` 页面并完成 Trigger 类型选择，但随后测试实现因错误捕获 `expect.poll(...).toMatchObject(...)` 的返回值而得到 `undefined`，在读取 `persistedCreatedTrigger.id` 时失败。

本轮针对该真实测试实现错误进行修复：将 Trigger 持久化等待改为独立的真实 HTTP 轮询函数，只有查询到 PostgreSQL 已持久化的目标 Trigger 后才返回实体；保留真实注册、登录、Browser Session、Frontend UI、Backend HTTP 和 Scheduler 持久化链路，不通过放宽业务断言或构造测试数据绕过问题。

**当前 Browser Gate 尚未由开发者重新执行，因此不得标记为通过。**

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：
  - 新增中文职责明确的 `waitForPersistedTrigger` 自动化等待函数；
  - 不再把 Playwright `expect.poll().toMatchObject()` 的断言结果误当作业务实体；
  - 继续通过真实 HTTP 查询确认 Trigger 已持久化，再读取其 `id` 进行 Scheduler 状态验证。
- `docs/04-errors/2026-08-25-browser-e2e-session-contract.md`：
  - 增加本轮 E2E 测试实现错误的根因、修复边界和验证要求。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：本轮已进入正式页面并完成 Select 交互，但在测试等待实体的实现错误处失败；已修复，等待开发者重新执行
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
修复 Browser E2E 测试实现的 API Client / Auth / Version / Route / Browser Session / UI Select / Persistence Poll Contract 漂移
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
