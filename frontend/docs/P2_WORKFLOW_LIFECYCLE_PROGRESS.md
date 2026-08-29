# P2 Workflow 生命周期前端实施进度

## 本阶段目标

形成 `Workflow → Version → Trigger → Execution → Runtime` 的完整前端业务闭环，优先消费后端已经实现并稳定提供的 HTTP Contract，不在前端虚构后端尚未提供的生命周期能力。

## 本轮 Contract 核对

后端 Workflow API 已提供：

- `GET /workflows`
- `POST /workflows`
- `GET /workflows/{workflow_id}`
- `PATCH /workflows/{workflow_id}`
- `DELETE /workflows/{workflow_id}`
- `GET /workflows/{workflow_id}/versions`
- `POST /workflows/{workflow_id}/versions`
- `POST /workflows/{workflow_id}/versions/{version_id}/publish`
- Workflow Trigger CRUD
- Scheduled Trigger Scheduler 状态查询
- Trigger Invoke
- Workflow Execution 创建、运行、取消、重试、恢复
- Execution Node 与 Runtime Trace 查询

## 已落实

`frontend/src/api/workflows.ts` 已覆盖 Workflow 单体查询、更新和删除 Contract。此前已覆盖的 Version、Trigger、Scheduler、Execution、Trace API 保持不变。

特别约束：

1. 前端不实现 Scheduler 调度算法；仅展示后端持久化调度状态。
2. Webhook Secret 不回显后端 secret_hash，仅展示配置状态。
3. Trigger Invoke 使用 `Idempotency-Key`，避免用户重复操作产生非预期重复执行。
4. Execution 的 retry/resume/cancel 仍由后端决定合法状态，前端只提供状态约束后的操作入口。
5. 错误区域不得直接展示原始 HTTP/后端内部错误文本。

## 下一步

1. Workflow 页面接入 `get/update/delete` 生命周期操作。
2. Workflow 页面完善发布前后的状态约束和危险操作确认。
3. Trigger 页面继续补齐名称/config 更新能力，并统一中文状态展示。
4. 将 Trigger Invoke 结果直接关联到 Runtime Execution 详情。
5. 增加 P2 专项 View/API 测试入口；主线完成前不执行全量回归。
6. 最终统一验证 Workflow、Trigger、Runtime 的端到端业务闭环。

## 完成标准

只有当 Workflow 创建/编辑/删除、版本创建/发布、Trigger 管理与调用、Execution 创建/运行/取消/重试/恢复、Runtime 查询和 Trace 均能通过真实 API Contract 连通，并具备 Loading/Empty/Error/Success 状态后，P2 才允许标记完成。
