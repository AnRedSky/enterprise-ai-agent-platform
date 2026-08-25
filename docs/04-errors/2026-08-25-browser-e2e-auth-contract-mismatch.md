# 2026-08-25 Browser E2E 注册请求契约不匹配

## 1. 实际失败

开发者在 `084adc1` 后重新执行 Workflow Trigger Browser Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Playwright 已成功进入实际用例，但在创建 E2E 用户时失败：

```text
Error: expect(received).toBeTruthy()
Received: false
at workflow-trigger-governance.spec.ts:23:27
```

失败点为 `/auth/register` HTTP 响应 `ok()` 为 false，尚未进入 Workflow / Scheduler 场景。

## 2. 根因

当前 Backend `/api/v1/auth/register` 的正式 `RegisterRequest` Contract 要求：

```text
username: 3-100 字符
password: 8-128 字符
```

而 E2E 测试此前发送的是：

```json
{
  "email": "...",
  "password": "...",
  "name": "..."
}
```

因此测试实现使用了与当前 Backend Contract 不一致的注册字段。该问题属于 E2E 测试实现与正式 API Contract 漂移，不是 Scheduler 生产逻辑故障。

## 3. 修复

已将 E2E 注册与登录统一改为正式 `username + password` Contract：

```json
{
  "username": "e2e-workflow-trigger-<timestamp>",
  "password": "TestPassword123!"
}
```

修复不新增 API Client，不修改 Backend Auth Contract，也不修改 Scheduler Runtime、数据库或生产 UI。

## 4. 后续验收

必须由开发者本地重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_frontend_regression_gate.ps1

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Workflow Trigger Browser Gate 在新的本地结果反馈前仍不得标记为通过，Phase 2.4 仍不得标记为 Passed。
