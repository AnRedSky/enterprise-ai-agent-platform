# Frontend P2 长期主线任务记录

## 当前阶段

**P2 — Workflow / Trigger → Runtime 完整业务闭环**

### 已完成

- Workflow 编辑、删除、发布约束
- Trigger 创建、编辑、启用/禁用、删除
- Trigger 启用前 Published Workflow 约束
- Manual Trigger → Workflow Execution → Runtime
- Scheduler `last_execution_id` → Runtime Execution 直接导航
- Webhook Trigger → Workflow Runtime Observation 导航
- Runtime Execution run / cancel / retry / durable resume
- Runtime Workflow ID / Version ID 展示
- Runtime 来源上下文与 Workflow ID 查询

### 当前进行中

1. Webhook 单次事件 → 精确 Execution ID 的关联，需要以后端现有事件/Execution Contract 为事实来源。
2. Retry / Resume 后的父 Execution 关系展示。
3. Trigger / Execution / Trace / Audit 的统一关联展示。
4. P2 阶段专项自动化测试与本地手动验收。

## 本轮实施原则

1. 以后端已经存在的 API Contract 为唯一业务事实来源。
2. Scheduler `last_execution_id` 是唯一允许直接导航的 Scheduler Execution 标识，不使用 `last_run_at` 推断 Execution。
3. Webhook 当前前端没有合法的 `last_execution_id` Contract，因此只导航到 Workflow + Trigger 的 Runtime Observation 上下文，不伪造 Execution ID。
4. 前端不重实现 Scheduler slot、Webhook authentication、idempotency、retry/recovery 状态机。
5. 每个主线功能采用原子提交。
6. 技术实现与设计决策同步记录到 `frontend/docs`。
7. P2 主线完成前只建立阶段专项测试脚本，不执行全局测试。

## 当前验收

- [x] Scheduler 状态卡显示后端 `last_execution_id`。
- [x] Scheduler `last_execution_id` 可一键打开 `/runtime` 精确 Execution。
- [x] Scheduler Runtime URL 保留 `workflow_id` 与 `source=scheduler`。
- [x] Webhook Trigger 可打开 `/runtime`，携带 Workflow ID、Trigger ID 与 `source=webhook`。
- [x] Manual Trigger 返回的真实 Execution ID 直接进入 Runtime。
- [ ] Webhook 单次请求的真实 Execution ID 深链接。
- [ ] Retry / Resume 父子 Execution 可视化。
- [ ] Trigger / Execution / Trace / Audit 统一关联。
