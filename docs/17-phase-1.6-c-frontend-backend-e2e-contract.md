# Phase 1.6-C：Frontend / Backend Integration & Browser E2E Contract

> 本阶段建立 Backend Contract、Frontend Contract 之外的第三独立测试层。Browser / Frontend-Backend E2E 不复制 Backend regression、Migration、Real API 或 Frontend regression。

## 1. 阶段目标

验证 Workflow Trigger Governance 从真实浏览器入口到真实 Backend HTTP 的完整用户链路：

```text
Browser → Vue 3 UI → Frontend API client → FastAPI HTTP → Workflow Trigger → Workflow Execution → PostgreSQL
```

## 2. E2E Contract

真实浏览器场景覆盖：

1. 注册隔离 E2E 用户并登录。
2. 通过真实 Backend HTTP 创建 draft Workflow、Version 并发布。
3. 浏览器登录并进入 `/workflows/triggers`。
4. 选择 Published Workflow。
5. 创建 manual Trigger。
6. 验证 enabled 状态。
7. Invoke Trigger 并验证最近一次 Execution 为 completed。
8. Disable Trigger 并验证 UI 禁止 Invoke。
9. Re-enable Trigger。
10. Delete Trigger 并验证 inventory 消失。

治理边界同时验证：

- Tenant 不由前端提交。
- UI 通过 Trigger API，不直接调用 Execution Runtime。
- Disabled Trigger 的 Invoke action 在 UI 层不可用。
- Execution 结果来自真实 Backend response。

## 3. 实现范围

```text
frontend/playwright.config.ts
frontend/tests/e2e/workflow-trigger-governance.spec.ts
frontend/scripts/test/e2e/01_run_workflow_trigger_e2e.ps1
frontend/package.json
```

Playwright 使用显式 `Desktop Chrome` project，Gate 脚本通过 `--project="Desktop Chrome"` 执行。

## 4. 实际发现与修复

Phase 1.6-C 开发过程中实际发现：

1. Playwright project 未显式命名，导致 Gate 在测试启动前失败；已修复。
2. E2E 注册状态码断言与真实 Backend HTTP Contract 不一致；已修复为真实 `200/201`。
3. Element Plus Workflow Select 的内部 input 被 selected item 拦截；已调整稳定交互方式。
4. Published Workflow 文本在页面与 dropdown 同时出现；已限定 locator 范围，消除 strict mode violation。
5. Delete confirmation 存在多个“确定”按钮；已将 locator 限定到可见 MessageBox。

错误记录：

```text
docs/error-tracking/004-playwright-project-missing.md
```

其他 E2E 定位问题属于测试实现缺陷，均已通过测试代码修正并在最终 Gate 验证。

## 5. 最终验收结果

开发者本地最终执行：

```powershell
cd frontend
Remove-Item Env:API_BASE_URL -ErrorAction SilentlyContinue
npx playwright test --list --project="Desktop Chrome"
```

结果：

```text
Listing tests:
[Desktop Chrome] › workflow-trigger-governance.spec.ts:10:1
Total: 1 test in 1 file
```

正式 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

最终结果：

```text
✓ 1 [Desktop Chrome] … Workflow Trigger Governance completes the real browser contract (3.3s)
1 passed (3.9s)
[PASS] Phase 1.6-C browser E2E gate completed.
```

Phase 1.6-C **正式通过并关闭**。

同时已有独立 Gate 结果：

```text
Backend Real API       PASS — 14 passed
Frontend Vitest        PASS — 50 passed
Frontend build         PASS
Trigger Real HTTP      PASS — 开发者手动验收
Frontend UI            PASS — 开发者手动验收
Browser E2E             PASS — 1 passed
```

## 6. Gate 隔离

```text
Backend Gate
  Backend regression → Migration/head → Real API

Frontend Gate
  Frontend Vitest → production build

E2E Gate
  Browser → real Frontend → real Backend HTTP
```

三层继续保持独立，E2E 不调用 Backend regression、Alembic、Backend Real API Gate、Frontend Vitest 或 production build。

## 7. Phase 1.6 收口

Phase 1.6-A、1.6-B、1.6-C 均已完成，Workflow Trigger 从 Backend Contract 到真实浏览器的完整业务闭环已验收。

下一阶段不再继续扩展 manual Trigger；进入 **Phase 1.7 Workflow Trigger Expansion / Scheduling Contract**，第一项为 `Phase 1.7-A-01 Scheduled Trigger Backend Contract`。
