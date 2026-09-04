# P2：Workflow Trigger → Webhook / Scheduler → Workflow Execution 可观测闭环

## 目标

将已经由后端实现的 Trigger、Webhook、Scheduler 与 Workflow Execution 能力在前端统一收敛到 Runtime Observation，不在浏览器重新实现后端状态机、调度算法、幂等或恢复规则。

## 关键 Contract 边界

当前后端存在两个需要严格区分的执行事实模型：

- `WorkflowExecution`：Workflow Trigger / Webhook / Scheduler 创建和生命周期管理的执行事实；Webhook `POST /api/v1/webhooks/{trigger_id}` 返回的 `execution_id` 属于该模型。
- `Execution`：Runtime Query 的通用运行时观测事实，由 `/api/v1/runtime/executions/{execution_id}` 查询；不能把 `WorkflowExecution.id` 未经 Contract 映射直接当成该接口的 ID。

因此，Webhook 单事件返回的真实 `execution_id` 应进入 Workflow Lifecycle 或 Runtime Correlation；只有后端明确提供 `Execution` 映射时，才能进入 Runtime Execution Detail。前端测试不得通过时间、列表排序或“最近执行”推断另一种 ID。

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

这样可以从 Runtime `Execution` 反向确认其实际执行的 Workflow 资产与发布版本。

### 3. Scheduler last_execution_id → Runtime

Scheduler 持久化状态读取后，前端直接使用后端返回的 `last_execution_id` 建立 Runtime 深链接：

- `execution_id=<last_execution_id>`
- `workflow_id=<current_workflow_id>`
- `source=scheduler`

页面不自行推断“最近执行”，不根据 `last_run_at` 查询或排序生成替代 ID。若 `last_execution_id` 属于 `WorkflowExecution`，必须先经过已有的 Workflow Lifecycle / Correlation Contract，而不是直接调用 Runtime Execution Detail。

### 4. Webhook → Workflow Lifecycle / Runtime Correlation

Webhook 单事件接口返回真实 `execution_id` 后，前端使用该 ID：

1. 进入 `/workflows/lifecycle`，携带 `workflow_id` + `execution_id` + `source=webhook`，精确定位本次 `WorkflowExecution`；
2. 进入 `/runtime?tab=correlations` 时，使用 `focus_type=execution` + `focus_id=<returned_execution_id>`，调用后端 Runtime Correlation Contract；
3. 不把该 `WorkflowExecution.id` 直接发送到 `/runtime/executions/{id}`，避免两个执行事实模型被混淆。

Webhook Contract 当前由后端 Correlation API 明确支持 `WorkflowExecution` → Trace / Audit / Operator Action 关联，因此可以覆盖单次 Webhook Execution 的精确观测闭环。

### 5. Manual Trigger

Manual Trigger 成功调用后直接携带返回的真实 Workflow Execution ID 进入 Workflow Lifecycle；需要 Runtime 观测时通过 Runtime Correlation Contract 定位，不在前端假设其等同于通用 Runtime `Execution` ID。

### 6. Webhook 边界

后端 Webhook Contract 为 `POST /api/v1/webhooks/{trigger_id}`，认证使用 `X-Webhook-Secret`，可选 Idempotency-Key / X-Request-ID。Frontend 不在浏览器模拟 Webhook authentication、duplicate claim 或 Execution 创建；Trigger Governance 页面只展示 Webhook endpoint 与配置状态。

### 7. Scheduler 边界

Frontend 只读取 Scheduler 持久化状态，不计算 slot、next-run、misfire、lease 或 recovery。Scheduler 产生的 Workflow Execution 最终通过明确的 Lifecycle / Correlation Contract 进入可观测链路。

## 验收标准

- Scheduler `last_execution_id` 可以在其真实 Contract 对应的页面打开目标执行事实。
- Runtime URL 保留 `workflow_id` 与 `source=scheduler` 上下文。
- Webhook Trigger 可以直接定位对应 Workflow Execution，并携带 Trigger / source 上下文。
- Webhook 单请求返回的真实 `execution_id` 可以打开 Workflow Lifecycle 精确执行上下文。
- Webhook 返回的真实 `execution_id` 可以通过 Runtime Correlation Contract 定位 Execution、Trace、Audit 关联事实。
- 不把 `WorkflowExecution.id` 未经 Contract 映射直接冒充 Runtime `Execution.id`。
- Runtime 可以按 Workflow ID 筛选通用 Runtime Execution。
- Runtime Execution 详情同时展示 Workflow ID / Version ID、Timeline、Workflow Trace。
- 不新增浏览器侧 Scheduler / Webhook 状态机。
- 不把 `last_run_at`、时间排序结果冒充 `last_execution_id`。
- P2 主线完成前不执行全局测试；本阶段测试使用 Runtime/Trigger 定向脚本。

## 回归记录：Webhook Runtime E2E

本地反馈曾出现：Webhook 返回的 `execution_id` 被直接导航到 `/runtime?tab=executions` 后，页面打开抽屉但 Runtime Detail 查询失败，随后测试对“运行记录详情”的文本断言又与错误提示产生 strict-mode 冲突。

根因不是 UI 文本，而是测试把 `WorkflowExecution.id` 当成 Runtime Query 的 `Execution.id`。后端 Webhook Service 创建的是 `WorkflowExecution`；Runtime `/runtime/executions/{id}` 查询的是独立的 `Execution` 模型。修复方式是让 E2E 按真实 Contract：

- Webhook response `execution_id` → Workflow Lifecycle 精确深链；
- 同一 ID → Runtime Correlation `focus_type=execution` 精确关联查询；
- Trigger 禁用 / 删除仍通过真实 UI 操作，并验证 409 / 404 生命周期安全边界；
- 不修改 Runtime UI 来迁就错误的 ID 模型假设。

同时保留 URL 对完整 UUID 的严格断言，UI 文本只断言稳定的页面/关联工作台语义，不依赖长 UUID 的视觉缩略格式。

## 当前状态

- Scheduler `last_execution_id → Runtime`：已实现，但必须遵循后端实际执行事实模型。
- Webhook Trigger → Workflow Lifecycle：已通过真实返回 `execution_id` 建立精确深链。
- Webhook → Runtime Correlation：已通过真实 `execution_id` 建立精确关联查询。
- Runtime 来源上下文：已实现。
- Webhook authentication / duplicate / disabled / deleted 生命周期回归：E2E 已覆盖。
- 下一项：继续 P2 专项自动化与本地真实 API / E2E 验收，不重复实现 Organization、Scheduler 基础流、Manual Trigger 或 Retry / Resume 已完成能力。
