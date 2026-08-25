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

当前最新提交为 `293773d`，本轮在 `6d4f206` 修正 Browser E2E 数据库重置 Backend 根路径之后，继续修正 Browser E2E 隔离运行器的 Frontend 根目录计算，确保 Playwright 在 `frontend` 根目录执行。

开发者本地实际结果：

```text
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py：BROWSER_E2E_DATABASE_RESET_OK
```

随后执行 Organization / Model Provider / Workflow Trigger 三个 Browser Gate 时，数据库重置均成功，但隔离运行器在启动 Playwright 前失败，原因是 `npm run test:e2e` 被错误地在仓库根目录执行，仓库根目录不存在 `package.json`。

以上 Browser 结果来自开发者本地实际执行反馈。本轮 Frontend / Browser 修复完成后，必须重新执行对应 Gate，当前不得提前宣称 Browser E2E 已通过。

## 本轮工程变更

- `backend/scripts/test/e2e/00_reset_browser_e2e_database.py`：修正直接脚本启动时的 Backend 根路径计算，当前本地数据库重置已实际成功。
- `frontend/scripts/test/e2e/00_run_isolated_test.ps1`：修正隔离运行器的前端根目录计算，从仓库根目录改为 `frontend` 根目录；Backend 根目录由仓库根目录显式推导。
- `docs/04-errors/2026-08-25-browser-e2e-reset-import-failure.md`：记录 Browser E2E 数据库重置 import/path 错误及修复。
- `docs/04-errors/2026-08-25-browser-e2e-isolated-runner-root.md`：记录隔离运行器错误在仓库根目录执行 npm 导致 `package.json` 不存在的问题及修复。
- 未修改生产业务代码、Organization / Tenant 约束、Browser 测试断言或 Provider 实现；本次修复仅纠正测试 Gate 的工作目录。

## 测试入口纠正

Frontend 与 Backend Gate 必须在各自工作目录执行。Browser E2E 隔离运行器必须自行切换到 `frontend` 根目录后执行 Playwright；不得依赖调用者当前工作目录。

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