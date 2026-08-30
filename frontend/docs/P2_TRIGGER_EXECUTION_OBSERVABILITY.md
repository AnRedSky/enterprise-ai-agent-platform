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

### 3. Execution Observation

Runtime 详情继续直接读取后端 Execution、Timeline、Workflow Trace，并保留 run / cancel / retry / resume 操作直接调用后端 Contract 的原则。

### 4. Webhook 边界

后端 Webhook Contract 为 `POST /api/v1/webhooks/{trigger_id}`，认证使用 `X-Webhook-Secret`，可选 Idempotency-Key / X-Request-ID。Frontend 不在浏览器模拟 Webhook authentication、duplicate claim 或 Execution 创建；Trigger Governance 页面只展示 Webhook endpoint 与配置状态。

### 5. Scheduler 边界

Frontend 只读取 Scheduler 持久化状态，不计算 slot、next-run、misfire、lease 或 recovery。Scheduler 产生的 Execution 最终统一进入 Runtime Observation。

## 验收标准

- Runtime 可以通过 `execution_id` 直接打开 Execution 详情。
- Runtime 可以按 Workflow ID 筛选 Execution。
- Execution 详情同时展示 Workflow ID / Version ID、Timeline、Workflow Trace。
- 来源上下文可以区分 Workflow Trigger、Webhook、Scheduler。
- 不新增浏览器侧 Scheduler / Webhook 状态机。
- P2 主线完成前不执行全局测试；本阶段测试应使用 Runtime/Trigger 定向脚本。

## 后续

下一项继续补齐 Trigger Governance 到 Runtime 的直接导航与来源关联，随后进入 P2 的阶段性专项测试；不提前进入全局回归。
