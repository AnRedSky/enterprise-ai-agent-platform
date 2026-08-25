# 2026-08-25 Workflow Trigger Browser E2E Scheduler 状态选择器冲突

## 1. 现象

本地执行 Phase 2.4 Workflow Trigger Browser Gate 时，Scheduler 状态面板已经能够显示并完成真实后端状态轮询，但测试在校验 `catch_up_limit` 时失败。

失败位置：`frontend/tests/e2e/workflow-trigger-governance.spec.ts` 第 136 行。

原断言：

```ts
await expect(page.getByText("10")).toBeVisible();
```

Playwright strict mode 发现页面存在多个包含 `10` 的元素，其中包括 `catch_up_limit = 10` 和时间戳，因此无法唯一定位。

## 2. 根因

测试使用页面级文本选择器匹配业务字段值，没有把断言范围限定到 Scheduler 状态卡片，也没有使用表格单元格的语义角色。

该问题属于 Browser E2E 测试定位不稳定，不是 Scheduler API Contract、Runtime 调度算法或数据库持久化错误。

## 3. 修复

将 Scheduler 状态字段断言限定在 `.scheduler-card` 内，并使用 `getByRole("cell", { name, exact: true })` 精确匹配 `UTC`、`skip` 和 `10`。

这样既验证真实 UI 展示的 Scheduler 持久化字段，又避免页面其他时间戳或文本产生 strict mode 冲突。

## 4. 验证要求

必须在本地重新执行：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

本错误记录只记录已发生的失败及代码修复，不预填通过结果。
