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

当前远端 `main` 最新提交为 `c013ace`。该提交已修正 Workflow Trigger Browser E2E 暴露的 Scheduler 状态面板异步初始化渲染问题：选择 Scheduled Trigger 后立即显示状态面板，在初始化期间显示 loading / 提示。

开发者随后本地重新执行 Workflow Trigger Browser Gate，数据库隔离重置和 Scheduler 状态接口轮询均正常，但暴露出新的测试定位问题：`getByText("10")` 在页面中匹配到 `catch_up_limit` 与时间戳等多个元素，Playwright strict mode 失败。

## 本轮工程变更

- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`：将 Scheduler 状态字段断言限定在 `.scheduler-card` 内，并使用精确的表格单元格语义选择器，避免页面时间戳等非目标文本造成 strict mode 冲突。
- `docs/04-errors/2026-08-25-browser-e2e-scheduler-status-selector.md`：记录 Scheduler 状态字段选择器冲突、根因与修复。
- 未修改 Scheduler API Contract、Runtime 调度算法、slot / lease / misfire 规则或生产调度逻辑。

## 已完成的 Browser Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
Workflow Trigger Browser Gate：在修复 Scheduler 状态面板后继续暴露测试定位问题，当前已完成针对性修复，等待本地重新执行结果
```

以上结果以开发者本地实际反馈为准，不预填通过结果。

## Phase 2.4 当前任务

```text
Frontend Vitest + production build
      ↓
Browser Scheduler Gate 重新执行
      ↓
Backend default regression + Tenant Safe Real API Gate（再次确认）
      ↓
Scheduler 多实例 lease / misfire / Execution / Audit Trace Acceptance 汇总
      ↓
Phase 2.4 Passed 评估
```

当前不标记 Phase 2.4 Passed。必须等待 Workflow Trigger Browser Gate 修复后的本地实际结果，并完成后续 Backend Gate / Real API / Acceptance 汇总。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果。
