# 2026-08-25 Browser E2E Scheduler 状态面板渲染失败

## 1. 现象

本地执行 Phase 2.4 Workflow Trigger Browser Gate 时，数据库隔离重置成功，Playwright 能够启动，但在点击 Scheduled Trigger 的“调度状态”后，测试在 5 秒内找不到 `Scheduler 持久化状态`。

失败位置：`frontend/tests/e2e/workflow-trigger-governance.spec.ts` 第 114 行。

## 2. 根因

`frontend/src/views/workflow-triggers/index.vue` 原实现使用 `schedulerStatus` 作为调度状态卡片的唯一渲染条件：只有 Scheduler API 已经成功返回并写入 `schedulerStatus` 后，`Scheduler 持久化状态` 标题才会进入 DOM。

但 Scheduler Runtime 的持久化 Schedule 初始化是异步过程，前端已经针对“尚未初始化”实现了短暂重试。重试窗口内 `schedulerStatus` 必然为空，因此 UI 不应该把“状态尚未返回”错误表达为“状态面板不存在”。这会使真实 Browser E2E 在后端状态尚未完成初始化时提前失败。

## 3. 修复

将 Scheduler 状态卡片的渲染条件改为“已经选择 Scheduled Trigger”，而不是“已经拿到 Scheduler 状态”。

- 点击“调度状态”后立即显示 `Scheduler 持久化状态`。
- 请求进行中由 `v-loading` 表达状态。
- 后端状态尚未返回时显示明确的初始化提示。
- 后端返回正式 `SchedulerStatus` 后继续显示原有持久化字段。
- 不修改 Scheduler API Contract、调度算法、slot、lease、misfire 或测试断言。

## 4. 验证要求

必须在本地重新执行：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

本错误记录只记录已发生的失败及代码修复，不预填通过结果。