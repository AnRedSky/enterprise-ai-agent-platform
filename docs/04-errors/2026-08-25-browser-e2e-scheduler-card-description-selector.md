# 2026-08-25 Browser E2E Scheduler 状态卡片选择器失败

## 1. 实际失败

开发者在远端 `main` 提交 `cca981b` 后重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Workflow Trigger Browser E2E 在 Scheduler 状态接口轮询成功后失败：

```text
Locator: locator('.scheduler-card').getByRole('cell', { name: 'UTC', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found
```

失败位置：

```text
frontend/tests/e2e/workflow-trigger-governance.spec.ts:136
```

## 2. 根因

生产页面 `frontend/src/views/workflow-triggers/index.vue` 的 Scheduler 持久化状态使用 Element Plus `el-descriptions` 展示，而不是普通数据表格。

因此测试使用：

```ts
schedulerCard.getByRole("cell", { name: "UTC", exact: true })
```

错误地假设 Scheduler 状态区域提供稳定的表格 `cell` 语义。真实组件结构的稳定业务语义是“时区 / Misfire / Catch-up Limit”等描述项及其值，而不是具体 DOM role。

本次失败不是 Scheduler API、Runtime、PostgreSQL 持久化或调度算法错误；API 轮询已经成功获得正式 Scheduler Contract。

## 3. 修复

将 Browser E2E 断言改为针对实际 `el-descriptions` UI 语义：

```ts
await expect(schedulerCard.getByText("时区", { exact: true })).toBeVisible();
await expect(schedulerCard.getByText("UTC", { exact: true })).toBeVisible();
await expect(schedulerCard.getByText("Misfire", { exact: true })).toBeVisible();
await expect(schedulerCard.getByText("skip", { exact: true })).toBeVisible();
await expect(schedulerCard.getByText("Catch-up Limit", { exact: true })).toBeVisible();
await expect(schedulerCard.getByText("10", { exact: true })).toBeVisible();
```

该修复只调整 Browser E2E 对生产 UI 的定位方式，不修改 Scheduler API Contract、Runtime 调度算法、slot、lease、misfire、数据库持久化或生产业务逻辑。

## 4. 验证要求

修复后必须重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_frontend_regression_gate.ps1

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

在开发者提供新的本地执行结果之前，不得将 Workflow Trigger Browser Gate 标记为通过，也不得将 Phase 2.4 标记为 Passed。
