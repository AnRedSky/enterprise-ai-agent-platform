# Browser E2E：隔离运行器错误使用仓库根目录执行 npm

## 1. 现象

2026-08-25 本地 Browser E2E 数据库重置已经成功，但 Organization、Model Provider/Profile、Workflow Trigger 三个独立 Gate 均在真正启动 Playwright 前失败：

```text
npm error code ENOENT
npm error path D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\package.json
npm error enoent Could not read package.json
```

此前 `00_reset_browser_e2e_database.py` 已修复并能输出 `BROWSER_E2E_DATABASE_RESET_OK`，因此本次失败发生在隔离运行器切换到前端执行 `npm run test:e2e` 的阶段，而不是数据库重置阶段。

## 2. 根因

`frontend/scripts/test/e2e/00_run_isolated_test.ps1` 使用 `$PSScriptRoot` 计算前端根目录时向上移动了四级：

```text
frontend/scripts/test/e2e
  ↑ 1 test
  ↑ 2 scripts
  ↑ 3 frontend
  ↑ 4 repository root
```

因此 `$frontendRoot` 实际指向仓库根目录。隔离运行器随后在仓库根目录执行 `npm run test:e2e`，而仓库根目录没有 `package.json`，导致 `npm` 直接返回 `ENOENT`。

## 3. 修复

将隔离运行器的前端根目录计算改为向上三级，确保：

- 数据库重置仍在 `backend` 根目录通过 `uv run` 执行；
- Playwright 命令在 `frontend` 根目录执行；
- Organization、Model Provider/Profile、Workflow Trigger 三个 Gate 继续共享同一个隔离运行器；
- 不修改生产业务代码、Tenant / Organization 约束或 Browser 测试断言。

同时通过 `Split-Path $frontendRoot -Parent` 推导仓库根目录，再定位 `backend`，避免再次依赖错误的层级计算。

## 4. 验证要求

修复后必须由开发者本地重新执行三个 Browser Gate，并记录实际结果：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\03_run_model_provider_e2e.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

本错误记录不代表上述 Browser Gate 已通过；只有实际执行成功后才能更新 Phase / Acceptance 状态。
