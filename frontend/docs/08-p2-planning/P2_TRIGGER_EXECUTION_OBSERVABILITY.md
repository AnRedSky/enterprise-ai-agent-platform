# P2：Workflow Trigger → Webhook / Scheduler → Execution 可观测闭环

## 目标

将已经由后端实现的 Trigger、Webhook、Scheduler 与 Workflow Execution 能力在前端统一收敛到 Runtime Observation，不在浏览器重新实现后端状态机、调度算法、幂等或恢复规则。

## 本阶段实现

### 1. Runtime Execution 来源上下文

Runtime 支持通过路由查询参数标记来源：

- `source=workflow-trigger`：Workflow Trigger → Execution
- `source=webhook`：Webhook → Workflow Execution
- `source=scheduler`：Scheduler → Workflow Execution

来源仅用于前端可观测性展示，不作为后端业务判断条件。

### 2. Workflow 关联信息

Runtime Execution 列表增加 Workflow ID 查询条件，并在列表与详情展示：

- Workflow ID
- Workflow Version ID

这样可以从 Execution 反向确认其实际执行的 Workflow 资产与发布版本。

### 3. Scheduler last_execution_id → Runtime

Scheduler 持久化状态读取后，前端直接使用后端返回的 `last_execution_id` 建立 Runtime 深链接：

- `execution_id=<last_execution_id>`
- `workflow_id=<current_workflow_id>`
- `source=scheduler`

页面不自行推断“最近执行”，不根据 `last_run_at` 查询或排序生成替代 ID。

### 4. Webhook → Runtime Observation

Webhook Trigger 提供“查看 Webhook 运行”入口，导航到当前 Workflow 的 Runtime Observation，并携带：

- `workflow_id=<current_workflow_id>`
- `trigger_id=<webhook_trigger_id>`
- `source=webhook`

由于当前前端 Contract 没有假造 Webhook `last_execution_id` 字段，因此这里不伪造具体 Execution。具体 Webhook Execution 仍由后端真实 Execution / Trace Contract 提供。

### 5. Manual Trigger

Manual Trigger 成功调用后直接携带返回的真实 Execution ID 进入 Runtime：

- `execution_id=<returned_execution_id>`
- `workflow_id=<current_workflow_id>`
- `source=workflow-trigger`

### 6. Webhook 边界

后端 Webhook Contract 为 `POST /api/v1/webhooks/{trigger_id}`，认证使用 `X-Webhook-Secret`，可选 Idempotency-Key / X-Request-ID。Frontend 不在浏览器模拟 Webhook authentication、duplicate claim 或 Execution 创建；Trigger Governance 页面只展示 Webhook endpoint 与配置状态。

### 7. Scheduler 边界

Frontend 只读取 Scheduler 持久化状态，不计算 slot、next-run、misfire、lease 或 recovery。Scheduler 产生的 Execution 最终统一进入 Runtime Observation。

## 验收标准

- Scheduler `last_execution_id` 可以一键打开对应 Runtime Execution。
- Runtime URL 保留 `workflow_id` 与 `source=scheduler` 上下文。
- Webhook Trigger 可以直接进入对应 Workflow 的 Runtime Observation 上下文，并携带 Trigger ID。
- Manual Trigger 返回的真实 Execution ID 可以直接打开 Runtime 详情。
- Runtime 可以按 Workflow ID 筛选 Execution。
- Execution 详情同时展示 Workflow ID / Version ID、Timeline、Workflow Trace。
- 不新增浏览器侧 Scheduler / Webhook 状态机。
- 不把 `last_run_at`、时间排序结果冒充 `last_execution_id`。
- P2 主线完成前不执行全局测试；本阶段测试使用 Runtime/Trigger 定向脚本。

## 当前状态

- Scheduler `last_execution_id → Runtime`：已实现。
- Webhook Trigger → Runtime Observation：已实现，具体 Execution ID 继续由后端真实 Contract 提供。
- Runtime 来源上下文：已实现。
- 下一项：补齐 Webhook 事件/Execution 的后端关联字段或现有事件 Contract 后，再实现精确到单次 Execution 的 Webhook 深链接。
