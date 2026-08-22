# Phase 2.1-F Browser E2E：成员标题 Locator Strict Mode 错误

## 发生时间

2026-08-22

## 场景

Phase 2.1-F Browser E2E 本地 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
```

## 实际错误

Playwright 在 Organization Detail 页面执行：

```ts
await expect(page.getByText("成员")).toBeVisible();
```

失败原因是 `getByText("成员")` 在严格模式下匹配到 3 个元素：

1. “添加成员”按钮中的文本。
2. “成员”标题。
3. “暂无成员。”文本。

因此测试不是业务链路失败，而是 Browser E2E locator 不具备唯一性。

## 影响

2.1-F-A/F-B Browser E2E Gate 被阻断；Frontend Regression 不受影响。

## 修复

将 locator 收窄为语义明确且唯一的 heading：

```ts
await expect(
  page.getByRole("heading", { name: "成员", exact: true }),
).toBeVisible();
```

修复直接提交 `main`，符合项目开发准则禁止创建功能分支的要求。

## 验证状态

修复提交后尚未由开发者本地重新执行 Browser E2E Gate，因此不得将 2.1-F 标记为 Passed。

下一步必须重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\02_run_organization_e2e.ps1
```
