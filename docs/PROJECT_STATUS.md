# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery 已完成开发并已有本地 Acceptance 结果；Frontend API/UI 已完成实现与问题修复，当前继续进行 Frontend / Browser E2E 验收。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 已包含 Scheduler Browser E2E 的 UI 选择器修复、稳定 metadata test hooks，以及 Workflow Trigger E2E 的 API Client 依赖修复。

开发者最新本地执行表明，Frontend Regression Gate 已通过；Workflow Trigger Browser E2E 已进入实际 Playwright 场景，但在注册 E2E 用户阶段失败：测试发送的 `/auth/register` 请求使用 `email/name` 字段，与当前 Backend 正式 `username/password` Contract 不一致。

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：将注册与登录请求从 `email/name` 调整为正式 Backend `username/password` Contract；继续使用 Playwright `APIRequestContext` 访问真实 Backend HTTP，并保留 Scheduler metadata test hooks。
- `docs/04-errors/2026-08-25-browser-e2e-auth-contract-mismatch.md`：记录本次本地实际失败、Auth Contract 漂移根因、修复边界与重新验收要求。
- 未修改 Auth Backend Contract、Scheduler API Contract、Runtime 调度算法、slot / lease / misfire 规则、数据库持久化或生产调度逻辑。

## 已完成的 Browser Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过
Workflow Trigger Browser Gate：已进入实际浏览器场景，但当前因注册请求 Contract 不匹配失败；修复后等待开发者重新执行
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
修复 Browser E2E 测试实现的 Auth Contract 漂移
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
