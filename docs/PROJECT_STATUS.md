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

当前远端 `main` 已完成 Workflow Trigger Browser E2E 的 API Client、Auth、Workflow Version、正式路由、Browser Session Contract 对齐。最新开发者本地反馈显示 Frontend Regression Gate 已实际通过 79 tests，production build 也已通过；Browser E2E 已成功进入正式 `/workflows/triggers` 页面，但 Element Plus `el-select` 内部 readonly input 的 pointer event 被 suffix SVG 拦截，导致 Trigger 类型选择步骤超时。

本轮已完成针对该真实 UI Contract 的 E2E 修复：为 Trigger 类型 Select 增加稳定 `data-testid`，并让 Playwright 点击 Select 根节点；同时保留真实注册、登录、Browser Session、Frontend UI、Backend HTTP 和 Scheduler 持久化链路，不通过强制事件或放宽业务断言绕过问题。

**当前 Browser Gate 尚未由开发者重新执行，因此不得标记为通过。**

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：
  - 使用真实 `/auth/login` 返回的 `access_token`、`roles`、`user_id` 建立正式浏览器 Session；
  - 保持正式路由 `/workflows/triggers`；
  - 使用稳定 `workflow-trigger-type-select` test hook 点击 Element Plus Select 根节点。
- `frontend/src/views/workflow-triggers/index.vue`：
  - 为 Trigger 类型 `el-select` 增加 `data-testid="workflow-trigger-type-select"`；
  - 未修改生产业务逻辑、Router、Backend Auth Contract 或 Scheduler Runtime。
- `docs/04-errors/2026-08-25-browser-e2e-session-contract.md`：
  - 记录 Browser Session Contract 漂移及 Element Plus Select pointer-event Contract 问题、根因和修复边界。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：本轮进入正式页面后在 Element Plus Select 交互处失败；已修复，等待开发者重新执行
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
修复 Browser E2E 测试实现的 API Client / Auth / Version / Route / Browser Session / UI Select Contract 漂移
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
