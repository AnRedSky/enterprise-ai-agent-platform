# 2026-08-25 Browser E2E Route Contract 漂移

## 现象

开发者在远端 `main` 的 `8a03937` 基线执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Frontend Regression Gate 已实际通过：18 个测试文件、79 个测试通过，production build 通过。

Workflow Trigger Browser E2E 已进入真实 Playwright 场景，并完成真实 Backend HTTP 的注册、登录、Workflow 创建、Version 创建与 Publish；随后页面断言失败：

```text
Locator: getByText('Workflow Trigger Governance', { exact: true })
Expected: visible
Timeout: 5000ms
```

失败测试使用：

```text
await page.goto("/workflow-triggers");
```

## 根因

当前生产 Router 的正式 Workflow Trigger 路由是：

```text
/workflows/triggers
```

而 E2E 使用了不存在的旧路径：

```text
/workflow-triggers
```

由于未命中正式路由，认证守卫不会进入 Workflow Trigger 页面，Playwright 自然无法找到 `Workflow Trigger Governance` 页面标题。

## 修复

仅修复 `frontend/tests/e2e/workflow-trigger-governance.spec.ts` 的导航路径：

```text
/workflow-triggers
        ↓
/workflows/triggers
```

不修改生产 Router，不新增旧路径兼容入口，不创建兼容垫片。

## 边界

本错误不涉及：

- Backend Auth Contract；
- Workflow / Version API Contract；
- Scheduler API Contract；
- Scheduler Runtime 调度算法；
- PostgreSQL 持久化；
- lease / slot / misfire 规则。

## 重新验收

修复后必须由开发者重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

在获得新的本地实际结果前，不得将 Workflow Trigger Browser Gate 或 Phase 2.4 标记为 Passed。
