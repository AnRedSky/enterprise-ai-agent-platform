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
- Retry / Resume → Parent Execution → Runtime 关系追踪
- Trigger → Execution → Trace → Audit 四层统一关联展示

### 当前进行中

1. Webhook 单次事件 → 精确 Execution ID 的关联，需要以后端现有事件/Execution Contract 为事实来源。
2. P2 阶段专项自动化测试与本地手动验收。

## 本轮实施原则

1. 以后端已经存在的 API Contract 为唯一业务事实来源。
2. Scheduler `last_execution_id` 是唯一允许直接导航的 Scheduler Execution 标识，不使用 `last_run_at` 推断 Execution。
3. Webhook 当前前端没有合法的 `last_execution_id` Contract，因此只导航到 Workflow + Trigger 的 Runtime Observation 上下文，不伪造 Execution ID。
4. Retry / Resume 父子关系只使用后端 `retry_of_execution_id`、`resume_of_execution_id` 与 `resume_checkpoint_sequence`。
5. Trigger ID 只来自 Runtime 路由上下文或 Trace `data.trigger_id`；没有真实 ID 时显示未解析，禁止根据唯一 Trigger、时间或状态推断。
6. Audit 只按真实 `execution_id` 查询，不把相邻审计记录归属到当前 Execution。
7. 前端不重实现 Scheduler slot、Webhook authentication、idempotency、retry/recovery 状态机。
8. 每个主线功能采用原子提交。
9. 技术实现与设计决策同步记录到 `frontend/docs`。
10. P2 主线完成前只建立阶段专项测试脚本，不执行全局测试。

## 当前验收

- [x] Scheduler 状态卡显示后端 `last_execution_id`。
- [x] Scheduler `last_execution_id` 可一键打开 `/runtime` 精确 Execution。
- [x] Scheduler Runtime URL 保留 `workflow_id` 与 `source=scheduler`。
- [x] Webhook Trigger 可打开 `/runtime`，携带 Workflow ID、Trigger ID 与 `source=webhook`。
- [x] Manual Trigger 返回的真实 Execution ID 直接进入 Runtime。
- [x] Runtime 展示 Retry 来源 Execution。
- [x] Runtime 展示 Resume 来源 Execution。
- [x] Runtime 展示 Resume checkpoint sequence。
- [x] Runtime 展示当前 Execution 的派生 Retry / Resume Execution。
- [x] 父/子 Execution 可以通过真实 ID 一键导航。
- [x] Runtime 按 Execution ID 展示 Audit 审计记录。
- [x] Runtime 使用真实 Trigger ID 展示 Trigger 类型与详情。
- [x] Runtime 在同一详情中展示 Trigger / Execution / Trace / Audit 关联链路。
- [x] 无 Trigger ID 时不进行唯一 Trigger 推断。
- [ ] Webhook 单次请求的真实 Execution ID 深链接。
- [ ] P2 阶段专项自动化测试与本地手动验收。
