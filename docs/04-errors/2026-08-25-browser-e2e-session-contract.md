# 2026-08-25 Browser E2E Session Contract Mismatch

## 1. 现象

在 `c7c2a58` 修复正式前端路由后，开发者重新执行 Workflow Trigger Browser E2E，测试仍未进入 Workflow Trigger 页面：

```text
Locator: getByText('Workflow Trigger Governance', { exact: true })
Expected: visible
Timeout: 5000ms
```

测试已经使用正式路由 `/workflows/triggers`，但页面标题不可见。

## 2. 根因

Frontend Router 对非公开路由执行 `isAuthenticated()` 检查。正式前端 Session 存储在浏览器 `localStorage`：

- `enterprise_agent_access_token`
- `enterprise_agent_roles`
- `enterprise_agent_user_id`

本次 E2E 通过 Playwright `APIRequestContext` 完成真实注册、登录并取得 access token，但只在 API 请求中使用 `Authorization` Header，没有把真实登录结果建立到 Browser Context 的正式 Session 存储中。

因此 `page.goto("/workflows/triggers")` 触发认证守卫并进入登录页，Playwright 无法找到 `Workflow Trigger Governance`。

## 3. 修复边界

已在 `frontend/tests/e2e/workflow-trigger-governance.spec.ts` 中使用真实 `/auth/login` 返回的 `access_token`、`roles`、`user_id` 初始化浏览器 `localStorage`，使 Browser Session 与正式前端认证 Contract 一致。

本次没有：

- 修改生产 Router；
- 增加旧路由兼容入口；
- 修改 Backend Auth Contract；
- 修改 Scheduler Runtime、Repository、Migration 或调度算法。

## 4. 验证要求

必须重新执行 Workflow Trigger Browser Gate；只有开发者本地实际输出通过后，才能更新 Acceptance 为通过。

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

如果继续失败，应优先检查真实浏览器 Session、Frontend API Base URL、Backend HTTP Auth Contract，而不是放宽页面断言。
