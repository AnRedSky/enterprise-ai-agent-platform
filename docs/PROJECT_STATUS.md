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

当前远端 `main` 最新提交为 `4c970cb`。本轮先修正 Browser E2E 数据库重置 Backend 根路径，再修正隔离运行器的 Frontend 根目录计算；开发者随后完成 Organization 与 Model Provider Browser Gate，Workflow Trigger Browser Gate 暴露新的生产 UI 渲染问题。

开发者本地实际结果：

```text
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py：BROWSER_E2E_DATABASE_RESET_OK

Organization Browser Gate：3/3 passed
Model Provider Browser Gate：2/2 passed
Workflow Trigger Browser Gate：1 failed
```

Workflow Trigger 失败位置：点击 Scheduled Trigger 的“调度状态”后，Playwright 在 5 秒内找不到 `Scheduler 持久化状态`。失败并非数据库重置或隔离运行器问题。

## 本轮工程变更

- `frontend/src/views/workflow-triggers/index.vue`：修正 Scheduler 持久化状态卡片的渲染生命周期。选择 Scheduled Trigger 后立即渲染状态面板，在异步 Scheduler 状态初始化期间显示 loading / 初始化提示，成功后继续显示真实后端状态。
- `docs/04-errors/2026-08-25-browser-e2e-scheduler-status-panel.md`：记录 Workflow Trigger Browser E2E 暴露的 Scheduler 状态面板渲染问题、根因及修复。
- 未修改 Scheduler API Contract、Runtime 调度算法、slot / lease / misfire 规则，也未修改 Browser E2E 断言。

## 已完成的 Browser Gate

```text
Phase 2.1-F Organization Browser Gate：本地实际通过
Model Provider Browser Gate：本地实际通过
```

以上结果来自开发者本地反馈，可作为当前事实记录。

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