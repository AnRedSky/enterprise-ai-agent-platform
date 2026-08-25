# 2026-08-25 Browser E2E 缺失 api-client 模块失败

## 1. 实际失败

开发者在远端 `main` 的 `d714892` 后执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Workflow Trigger Browser E2E 未进入 Playwright 用例执行，直接在模块加载阶段失败：

```text
Error: Cannot find module '...\frontend\tests\e2e\support\api-client'
imported from ...\frontend\tests\e2e\workflow-trigger-governance.spec.ts
Error: No tests found.
```

## 2. 根因

`d714892` 将 `workflow-trigger-governance.spec.ts` 改为依赖：

```ts
import { createApiClient, apiPath, type ApiClient } from "./support/api-client";
```

但远端 `main` 中不存在 `frontend/tests/e2e/support/api-client.ts`，仓库内也未检索到对应正式实现。因此测试实现产生了悬空 import，导致 Playwright 在收集测试文件时直接失败。

该问题属于 Browser E2E 测试实现自身的依赖错误，不是 Scheduler API、Runtime、PostgreSQL 持久化或生产 UI Contract 错误。

## 3. 修复原则

根据开发准则，不新增第二套 API Client，也不创建兼容垫片。将该测试恢复为 Playwright 官方 `APIRequestContext`，继续通过 `API_BASE_URL` 指向真实 Backend HTTP，并保留 Scheduler metadata test hooks。

修复范围仅限：

- 删除不存在的 `./support/api-client` import；
- 在测试文件内使用 `playwright.request.newContext` 建立真实 HTTP 客户端；
- 保留 `scheduler-timezone`、`scheduler-misfire-policy`、`scheduler-catch-up-limit` 稳定测试钩子；
- 不修改 Scheduler Contract、Runtime、数据库或生产 UI。

## 4. 验证要求

修复后必须由开发者本地实际执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_frontend_regression_gate.ps1

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

在新的本地结果反馈前，不得将 Workflow Trigger Browser Gate 标记为通过，也不得将 Phase 2.4 标记为 Passed。
