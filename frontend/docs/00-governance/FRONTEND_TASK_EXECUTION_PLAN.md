# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移，并开始 Workflow 生命周期工作台公共模式收敛。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench；本轮新增 WorkflowLifecycle 第一批公共容器迁移。

## UI-04
状态：**Core Regression 已完成用户本地 targeted 验证，进入 UI-05。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：Workflow、RuntimeObservabilityOverview、AuditLogPanel、AgentWorkbench、DashboardOverview、KnowledgeWorkbench、ToolWorkbench；本轮继续收敛 WorkflowLifecycle。

### UI-04 Core Regression

本轮已完成 Agent UI-04 Permission 回归。用户本地最新反馈中 `tests/utils/agentContextState.test.ts` 8/8 通过；随后 `AgentUI04.test.ts` 已通过。此前剩余失败根因是测试环境 `el-button` stub 同时触发 fallthrough click 与 `$emit('click')`，导致 `getPublishedVersion` 被调用两次；修复为声明 `emits: ['click']` 后消除重复事件。

## UI-05 Form / Dialog / Drawer / Confirm

状态：**进行中：WorkflowLifecycle 第二阶段已完成 Backend Operator Action Availability 收口；下一步进入核心页面回归与后续页面选择。**

原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。

### ToolWorkbench

- 公共 `src/components/ui/ConfirmDialog.vue` 已接入停用、启用和解绑。
- 创建 Dialog 已完成名称必填、`input_schema` JSON 对象校验、提交 loading、成功关闭/重置、失败保留输入和响应式宽度。
- 用户本地 `Tools.test.ts` 8/8 通过，`ConfirmDialog.test.ts` 3/3 通过；合计 11/11 通过。
- 本轮本地失败已定位为测试夹具与 Element Plus 表格事件/渲染契约不一致，生产代码未被用于绕过测试。
- 设计记录：`docs/01-design/UI_05_TOOL_FORM_DIALOG_MIGRATION.md`。

### 第二个核心页面：WorkflowLifecycle

- 使用公共 `PageHeader`、`SurfaceCard`、`StatePanel`，统一页面标题、内容容器和 Loading / Empty / Error / Permission 状态。
- 保留真实 Workflow / Version / Trigger / Scheduler / Execution 关联和 Runtime 深链。
- Execution 操作按钮不再根据 `execution.status` 本地推断；统一消费 `/runtime/operator-actions/workflow-executions/{execution_id}` 返回的 `actions[]`，只展示后端 `allowed=true` 的 Run / Cancel / Retry / Resume。
- Availability Contract 的 `reason_code`、`requires_confirmation`、`requires_idempotency_key`、`idempotent` 与描述信息进入前端 API 类型边界，不复制后端状态机。
- Resume 不再把 `failed` 视为充分条件；后端 Availability 会执行 Durable Checkpoint Recovery Assessment，前端只接受后端最终的 `allowed / reason_code`，因此 `CHECKPOINT_NOT_ELIGIBLE` 等情况不会出现错误 Resume 入口。
- Manual Trigger 的 invoke / delete 同样消费 `/runtime/operator-actions/workflow-triggers/{trigger_id}` Availability；Scheduler 仍保持只读。
- 403 明确映射为 Permission；409 根据后端 detail 区分状态变化与 Idempotency / Result 冲突，不再统一误报为状态错误。
- Retry / Invoke 成功后以 Operator Action 返回的 `Result Resource` 为操作结果展示依据；Retry 继续展示 `retry_of_execution_id` lineage，Resume 展示 `resume_checkpoint_sequence`，随后重新拉取 Backend Execution / Availability，后端刷新是最终事实。
- Runtime / Trace / Audit 仍以真实 Execution / Workflow / Version / Durable ID 作为关联根，不在前端重新推导关系。
- Operator Action → Result Resource → Audit → Execution → Trace 的链路保持由后端治理；前端只展示和传递真实结果资源及关联 ID，不创建平行审计或状态机。
- Manual Trigger 与 Execution 操作统一使用 `ConfirmDialog`，提交期间防重复确认，取消后清理 target/action。
- 已确认 Scheduled / Webhook Trigger 配置存在真实 `PATCH /workflows/{workflow_id}/triggers/{trigger_id}` Contract；前端严格复用既有 `workflowApi.updateTrigger`。
- Scheduled 编辑严格使用后端 timezone / interval / misfire / catch-up Contract，不在前端计算 Scheduler `next_run_at`。
- Webhook 编辑只允许提交新 Secret；留空时不发送 Secret，页面不读取或回显后端 `secret_hash`。
- 归档 Workflow 不提供 Trigger 编辑/删除入口，保持只读观测边界。
- **第二阶段 targeted regression 已补充：Availability action filtering、Resume checkpoint eligibility、403 Permission、409 idempotency conflict、Retry Result Resource / lineage、Backend refresh。**
- 设计记录：`docs/01-design/UI_05_WORKFLOW_LIFECYCLE_MIGRATION.md`。

### RuntimeCorrelations Durable Fact 定位

- Runtime correlation Response 新增 `focused_traces` / `focused_audit` 后，前端 API 类型已对齐该 Contract。
- Trace focus 优先消费后端 `focused_traces`，即使目标 Trace 不在当前分页 `traces.items` 中也能展示具体 Durable Fact。
- Audit focus 优先消费后端 `focused_audit`，即使目标 Audit 不在当前分页 `audits.items` 中也能展示具体 Durable Fact。
- Trace / Audit 进入 Runtime correlation 或返回 WorkflowLifecycle 时均优先使用 focused Durable Fact 自身携带的真实 Execution / Workflow / Version ID。
- 列表分页保持原有 page/page_size 语义，不扩大分页、不复制后端关系查询、不通过时间、排序、索引或字符串推导关系。
- Regression 覆盖“目标不在当前分页但存在 focused fact”的 Trace / Audit 深链定位场景。
- 设计记录：`docs/01-design/UI_05_WORKFLOW_LIFECYCLE_EXECUTION_OPERATIONS.md`。

## 固定执行流程

```text
同步 main
  → 读取真实源码/API Contract
  → 一个核心页面
  → 公共模式迁移
  → targeted test
  → 设计文档
  → 原子提交
  → 用户本地完整验证
```

## 本地验证

ToolWorkbench：

```powershell
cd frontend
npm run test:unit -- --run tests/views/Tools.test.ts
npm run test:unit -- --run tests/components/ConfirmDialog.test.ts tests/views/Tools.test.ts
```

WorkflowLifecycle / RuntimeCorrelations / Trigger Management：

```powershell
cd frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts tests/views/WorkflowLifecycleTriggerManagement.test.ts
npm run build
npm run test:unit
npm run test:gate
```

本轮用户已反馈 `tests/e2e/workflow-webhook-runtime.spec.ts`：**1 passed (8.0s)**；同时已执行 `npm test`、`npm run build`、`npm run test:gate`，用户确认测试通过，但未提供完整长日志，因此这里只记录“用户确认通过”，不虚构具体测试数量或耗时。

远端执行环境不运行 Node/Vitest/build，因此本轮新改动仍需用户本地执行 targeted test；未实际执行的门禁不得标记为通过。

## 下一任务

继续 UI-05 主线：**先完成 WorkflowLifecycle 第二阶段本地 targeted regression，再根据结果进入下一个核心页面。** 后续页面必须继续复用 Backend Operator Action Availability Contract；不得恢复 `execution.status → action[]` 本地状态矩阵。Scheduler 仍保持只读，直到后端提供完整的 Scheduler Write Contract（配置修改、Trigger → Scheduler 同步、lease / misfire / idempotency 等）。不在前端虚构操作，不新增平行 API client、状态机或 Dialog。
