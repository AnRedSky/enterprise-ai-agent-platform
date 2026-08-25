# Scheduler 状态 API：异步初始化窗口导致 Browser E2E 首次查询 404

## 1. 现象

2026-08-25 Browser E2E 在 Scheduled Trigger 创建后立即点击“调度状态”，页面未显示 `Scheduler 持久化状态`。

## 2. 根因

Scheduler 状态 API 复用正式 `WorkflowSchedulerRepository`，并明确在持久化 Schedule 尚未初始化时返回 `404 Scheduler 状态尚未初始化`。Trigger 创建成功与 Scheduler Runtime 完成首次持久化初始化之间存在短暂异步窗口。

原 Frontend View 只请求一次状态 API，将该预期初始化窗口直接当作失败处理，因此用户在正常创建后立即查看状态时可能看不到持久化状态。

## 3. 修复

Frontend `loadSchedule` 保持只读 API Contract，不复制 Scheduler 调度、slot 或 misfire 规则；仅针对“尚未初始化”这一可预期状态进行有限次数重试，等待 Runtime 完成正式 Schedule 持久化。

同时补充 Vitest，验证首次返回初始化未完成、第二次返回正式 Scheduler Contract 时页面能够正常展示状态且不产生错误提示。

## 4. 边界

重试只覆盖 Scheduler 初始化窗口，不改变后端 404 Contract，也不由前端计算 `next_run_at`、lease、misfire 或 slot。
