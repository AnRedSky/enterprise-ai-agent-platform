# Frontend P2 长期主线任务记录

## 当前阶段

**P2 — Workflow / Trigger → Runtime 完整业务闭环**

### 已完成

- Workflow 编辑、删除、发布约束
- Trigger 创建、编辑、启用/禁用、删除
- Trigger 启用前 Published Workflow 约束
- Manual Trigger → Workflow Execution → Runtime
- Runtime Execution run / cancel / retry / durable resume
- Runtime Workflow ID / Version ID 展示
- Runtime 来源上下文与 Workflow ID 查询

### 当前进行中

1. Trigger Governance → Runtime Execution 直接导航。
2. Scheduler `last_execution_id` → Runtime Execution。
3. Webhook 入口 → Execution 可观测关联。
4. Retry / Resume 后的父 Execution 关系展示。
5. Trigger / Execution / Trace / Audit 的统一关联展示。

## 实施原则

1. 以后端已经存在的 API Contract 为唯一业务事实来源。
2. 前端不重实现 Scheduler slot、Webhook authentication、idempotency、retry/recovery 状态机。
3. 每个主线功能采用原子提交。
4. 技术实现与设计决策同步记录到 `frontend/docs`。
5. P2 主线完成前只建立阶段专项测试脚本，不执行全局测试。

## 下一阶段验收

- Trigger 页面可直接打开最近 Scheduler Execution。
- Webhook 入口可从治理页面定位对应 Execution。
- Runtime 可根据 Workflow、Trigger 来源和 Execution ID 形成闭环。
- Retry / Resume 创建的新 Execution 能追溯原 Execution。
