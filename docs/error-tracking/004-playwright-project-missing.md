# 004：Playwright Desktop Chrome Project 未定义导致 Phase 1.6-C E2E Gate 阻塞

## 发生阶段

Phase 1.6-C Frontend / Backend Integration & Browser E2E Contract。

## 实际错误

执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Gate 调用：

```text
npm run test:e2e -- --project="Desktop Chrome"
```

Playwright 返回：

```text
Error: Project(s) "Desktop Chrome" not found. Available projects: ""
```

Chromium 已成功安装，因此本次阻塞不是浏览器二进制缺失。

## 根因

`frontend/playwright.config.ts` 原先只在顶层 `use` 中展开：

```ts
...devices["Desktop Chrome"]
```

但没有在 `projects` 中声明名为 `Desktop Chrome` 的 Playwright project。

E2E Gate 脚本通过 `--project="Desktop Chrome"` 指定项目，两者配置契约不一致。

## 影响

Phase 1.6-C Browser E2E Gate 在测试用例启动前即失败，因此不能据此判断浏览器到 Vue UI、Backend HTTP 和 Workflow Trigger Governance 链路是否通过。

## 修复方案

在 `frontend/playwright.config.ts` 中显式定义：

```ts
projects: [
  {
    name: "Desktop Chrome",
    use: {
      ...devices["Desktop Chrome"],
    },
  },
],
```

同时保留顶层 `use` 中的 baseURL、trace、screenshot 配置，确保 Gate 脚本与 Playwright 配置使用同一个稳定的 project name。

## 预防措施

1. E2E Gate 脚本中使用的 `--project` 名称必须与 `playwright.config.ts` 的 `projects[].name` 一致。
2. 新增或修改 Browser E2E Gate 后，应至少执行 `npx playwright test --list --project="Desktop Chrome"` 验证项目配置可解析。
3. Chromium 安装成功不能视为 E2E Gate 配置正确；必须区分浏览器依赖、Playwright project 配置和实际测试链路三个层次。
4. Phase 1.6-C 关闭前仍必须由开发者本地实际执行 Browser E2E Gate，并独立通过 Backend / Frontend Gate。

## 验证命令

修复后首先执行：

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
```

随后执行正式 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

## 实际验证结果

本记录创建时仅完成配置修复，正式 Browser E2E Gate 尚未重新执行。因此本错误记录不声明 Phase 1.6-C 已通过。
