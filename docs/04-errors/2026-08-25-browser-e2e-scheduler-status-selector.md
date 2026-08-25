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

## 5. 后续失败：Scheduler 状态标题 strict mode 冲突

开发者在上述修复后的本地 Browser Gate 中继续执行，新的失败发生在 Scheduler 状态面板打开后的标题断言：

```text
expect(locator).toBeVisible() failed
Locator: getByText('Scheduler 持久化状态')
strict mode violation: resolved to 2 elements
```

两个匹配项分别是状态卡片标题 `Scheduler 持久化状态` 和初始化提示 `Scheduler 持久化状态正在初始化，请稍候刷新。`。

根因仍属于 Browser E2E 页面级文本选择器过宽：初始化提示包含标题文本，导致 `getByText` 非精确匹配产生两个元素。

修复为：

```ts
await expect(page.getByText("Scheduler 持久化状态", { exact: true })).toBeVisible();
```

本次修复同样不修改 Scheduler API Contract、Runtime 调度算法、持久化模型或生产调度逻辑，仅收紧 E2E 选择器语义。

修复后必须重新执行 Frontend regression、production build 与 Workflow Trigger Browser Gate；在开发者本地实际反馈前，不得记录 Browser Gate Passed。
