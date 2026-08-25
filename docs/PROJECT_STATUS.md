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

当前远端 `main` 已完成 Workflow Trigger Browser E2E 的 API Client、Auth、Workflow Version、正式路由、Browser Session、Element Plus Select、Trigger 持久化实体等待以及 Scheduler UI 异步初始化同步 Contract 对齐。开发者最新本地反馈中，Workflow Trigger Browser E2E 已完成真实 Trigger 创建、真实 Scheduler API 状态确认和 Scheduler UI 状态展示，随后在最终 PostgreSQL Trigger Config 断言处失败。

本轮失败并非生产 Contract 错误，而是 E2E 断言仍要求旧的两字段 Config。正式 Scheduler Contract 已包含 `misfire_policy` 与 `catch_up_limit`，Backend 对缺省配置补齐 `skip / 10` 默认值，因此真实持久化实体为四字段 Config。测试已按正式 Contract 修正为完整断言。

**当前 Browser Gate 尚未由开发者重新执行，因此不得标记为通过。**

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：
  - 将 Scheduled Trigger 持久化 Config 断言从旧的两字段契约调整为完整正式契约；
  - 同时验证 `timezone / interval_seconds / misfire_policy / catch_up_limit`；
  - 保留最终 `toEqual`，不降低真实持久化断言强度。
- `docs/04-errors/2026-08-25-browser-e2e-trigger-config-contract.md`：
  - 记录 Trigger 持久化 Config 断言落后于正式 Scheduler Contract 的工程错误、根因、修复边界和本地验收要求。

## 已完成的 Browser / Frontend Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Frontend Regression Gate：本地实际通过（79 passed + production build）
Workflow Trigger Browser Gate：已完成真实 Trigger 创建、Scheduler API 状态确认及 Scheduler UI 验收；当前在最终持久化 Config 断言处发现 Contract 漂移，测试已修复，等待开发者重新执行
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
修复 Browser E2E 测试实现的 API Client / Auth / Version / Route / Browser Session / UI Select / Persistence Poll / Scheduler UI Sync / Persisted Config Contract 漂移
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
