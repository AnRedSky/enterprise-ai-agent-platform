# 2026-08-25 Browser E2E：Scheduler UI 初始化时序竞争

## 1. 现象

开发者在远端 `main` 基线 `10be607` 上执行 Workflow Trigger Browser E2E 时，真实 Trigger 已完成创建，真实 Backend HTTP 轮询也已经能够读取 PostgreSQL 持久化的 Scheduler 状态，但页面最初点击“调度状态”时仍处于 Scheduler 初始化窗口。

测试随后直接断言 `.scheduler-card` 内的 `scheduler-timezone`，实际 DOM 只有 Scheduler 卡片骨架，`v-if="schedulerStatus"` 下的状态字段尚未渲染，因此出现：

```text
expect(locator).toHaveText(expected) failed
Locator: locator('.scheduler-card').getByTestId('scheduler-timezone')
Expected: "UTC"
Error: element(s) not found
```

## 2. 根因

这不是 Backend Scheduler Contract 缺失，也不是 API 响应字段缺失。

真实页面的 `loadSchedule()` 会在 Trigger 创建后立即查询 Scheduler 状态。Scheduler Runtime 的持久化初始化是异步过程，首次查询可能返回 `404 / Scheduler 状态尚未初始化`。当前页面实现只在固定的短窗口内重试；而 Browser E2E 在确认真实 API 已经可读后立即读取页面 DOM，形成了两个真实时序：

```text
Browser 首次点击调度状态
        ↓
Frontend Scheduler 查询
        ↓
Backend Scheduler 初始化尚未完成
        ↓
页面暂时没有 schedulerStatus

同时

Browser E2E 真实 HTTP 轮询
        ↓
PostgreSQL Scheduler 状态完成持久化
        ↓
API 已经可读
```

因此测试看到的是“Backend 已经 ready、Frontend 本次查询仍未刷新”的瞬间状态。

## 3. 修复边界

本轮只调整 Browser E2E 测试同步策略，不修改 Scheduler 调度算法、持久化模型、misfire、lease 或 Trigger Contract。

修复后的测试流程为：

1. 浏览器通过真实登录建立 Session；
2. 浏览器真实创建 Scheduled Trigger；
3. 通过真实 HTTP 查询确认 Trigger 已持久化；
4. 通过真实 HTTP 轮询确认 Scheduler 状态已经持久化并符合 Contract；
5. 如果页面首次查询尚未渲染 Scheduler 字段，则点击生产页面提供的“刷新”按钮；
6. 最终仍然通过真实页面 `data-testid` 验证 `timezone / misfire_policy / catch_up_limit`。

这样既不通过固定 sleep 掩盖问题，也不构造测试数据，更不降低业务断言。

## 4. 验证要求

必须由开发者在本地重新执行：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

只有出现 Playwright `1 passed` 且脚本最终输出 `[PASS]`，才能将 Workflow Trigger Browser Gate 标记为通过。

之后继续按 `docs/PROJECT_STATUS.md` 的顺序执行 Frontend Regression、Backend Regression、Tenant Safe Real API 以及 Phase 2.4 Acceptance 汇总。
