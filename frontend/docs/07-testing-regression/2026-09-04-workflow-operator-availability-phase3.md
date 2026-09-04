# WorkflowLifecycle Phase 3 Regression — Trigger Operator Availability

日期：2026-09-04

## 目标

在 WorkflowLifecycle 第二阶段已经将 Execution 操作收口到 Backend Operator Action Availability 后，本阶段继续完成 Trigger `invoke / enable / disable / delete` 的同一治理模式迁移。

## 实施结论

- Trigger 操作资格统一读取 `/runtime/operator-actions/workflow-triggers/{trigger_id}` 的 `actions[]`。
- `allowed=true` 才允许进入操作确认；Availability 未加载或 action 不存在时不允许提交。
- `reason_code` 直接用于不可用提示与 Availability 展示，不在前端复制 Trigger 状态矩阵。
- `enable / disable / delete` 使用 canonical Operator Action endpoint，并发送 `confirm=true`。
- `invoke` 保持 `Idempotency-Key`，成功结果继续使用后端返回的 Result Resource。
- 每次 Trigger Operator Action 成功后重新读取 Trigger、Execution、Availability 与 Scheduler 只读数据，Backend refresh 是最终事实源。
- 403 保持 Permission 反馈；409 区分状态冲突与 Idempotency / Result 冲突。
- Scheduler 仍保持只读，没有新增未经后端确认的写接口。
- Runtime / Trace / Audit 深链继续使用真实 Durable ID，不新增平行状态机或审计模型。

## 定向测试

新增：

- `frontend/tests/api/workflow-trigger-operator-availability.test.ts`
- `frontend/tests/views/WorkflowLifecycle.operator-availability.test.ts`

覆盖：

1. canonical Trigger enable / disable / delete endpoint。
2. `confirm=true`。
3. Invoke `Idempotency-Key`。
4. backend `allowed` 驱动操作资格。
5. `reason_code` 展示与拒绝反馈。
6. Trigger 操作成功后的 Backend refresh。
7. 403 Permission 与 409 state / idempotency conflict。

## 2026-09-04 本地反馈回归修复

用户在最新 `frontend` 分支执行 `npm run build` 与 `npm run test:gate` 后发现两类阻塞：

### 1. TypeScript Contract 类型收窄

现象：

`OperatorActionName` 同时包含 Execution 与 Trigger action，而模板中的 `triggerActionText` 只覆盖 Trigger action。直接使用 `triggerActionText[item.action]` 会触发 TS7053。

根因：

Backend Availability 的 `actions[]` 类型是完整的 `OperatorActionName` 联合类型，不能把它直接当作 `TriggerAction` Record 的索引。

修复：

- 在 `WorkflowLifecycle.vue` 增加 `displayTriggerAction(action: OperatorActionName)` 展示边界函数。
- 模板统一通过该函数读取 Trigger action 文本。
- 不修改 Backend Contract、不扩张 Trigger action 枚举，也不复制第二套 action 映射。

提交：`fix: type workflow trigger action labels`

### 2. Trigger 管理测试与真实 Availability 门禁不一致

现象：

`WorkflowLifecycleTriggerManagement.test.ts` 中删除 Trigger 的测试收到 `ElMessage.warning is not a function`，随后无法进入确认态；此前测试 fixture 也没有提供 Trigger Operator Availability。

根因：

Phase 3 将 Trigger 删除操作改为后端 Availability 驱动。旧测试只 mock 旧的 Trigger CRUD 方法和 `ElMessage.success/error`，没有覆盖新增的 `triggerAvailability` API 及 warning 消息入口。

修复：

- 补齐 `workflowApi.triggerAvailability` mock，并返回允许 `invoke / enable / disable / delete` 的测试 Availability。
- 补齐 `workflowApi.executionAvailability` mock，使页面详情加载链完整且 deterministic。
- 补齐 `ElMessage.warning` mock。
- 保留原有删除确认、取消不提交、DELETE contract 以及 refresh 断言，不降低生产代码的 Availability 门禁。

提交：`fix: align trigger lifecycle test mocks`

### 3. 生命周期测试错误依赖表格 DOM 文本

现象：

定向测试出现大量“期望 `订单审批` / `e1` / `Runtime 诊断`，实际只得到 PageHeader 文本”的失败，共 23 个断言失败。失败集中发生在 `WorkflowLifecycle.test.ts`。

根因：

测试使用的 `el-table` / `el-table-column` stub 不渲染真实列 slot，因此表格中的 Workflow/Execution 数据不会进入 `wrapper.text()`。这属于测试渲染契约问题，而不是后端数据缺失；继续扩大生产 DOM 或修改表格组件以迎合测试都会产生不必要耦合。

修复：

- 增加 `waitForReady()`，以组件公开的 `pageState === "success"` 作为页面加载完成条件。
- Workflow、Version、Trigger、Execution 数据断言改为直接验证组件真实状态，而不是依赖被 stub 隐藏的表格文本。
- 深链诊断仍验证真实 `trace_id` / `audit_id`，并保留“反向诊断上下文”“继续 Trace/Audit 诊断”等既有 UX 契约。
- 详情错误断言与当前 `StatePanel` 文案统一为“工作流详情加载失败”。

提交：`test: align workflow lifecycle assertions with rendered contracts`

### 4. Trigger 成功操作后的 loading 状态阻止了关闭确认态

现象：

保存 scheduled Trigger 或删除 Trigger 成功后，测试发现 `triggerEditor.trigger` / `deleteTriggerTarget` 仍保留目标对象。

根因：

成功处理函数在 `triggerEditorLoading` / `deleteTriggerLoading` 仍为 `true` 时调用带 loading guard 的取消函数，取消函数为了防止用户重复操作直接 return，导致成功路径无法清理状态。

修复：

- 为编辑器、删除确认、启停确认分别增加成功路径专用 reset 函数。
- 用户主动取消仍保留 loading guard，避免中途操作破坏请求状态。
- 成功 API 返回后先 reset dialog/target，再执行 Backend refresh。
- 不改变 Operator Availability 门禁和 canonical API 调用。

## 2026-09-04 后续本地反馈：详情错误 StatePanel 选择器

现象：

用户执行定向测试后剩余 1 个失败：`详情失败后支持重新加载`。测试期望 `StatePanel.title === "工作流详情加载失败"`，实际读取到 `"暂无版本"`。

根因：

`WorkflowLifecycle` 在详情加载失败时保持页面级 `pageState === "success"`，并在版本区域渲染一个 `StatePanel(state="empty", title="暂无版本")`；详情失败状态随后以另一个 `StatePanel(state="error", title="工作流详情加载失败")` 追加渲染。测试使用 `findComponent(StatePanel)` 只返回第一个匹配组件，因此误把版本空状态当成详情错误状态。

修复：

- 不改变生产页面状态模型：详情失败仍是局部错误，不把整个 WorkflowLifecycle 页面误标为 page-level error。
- 测试改为从 `findAllComponents(StatePanel)` 中按 `title === "工作流详情加载失败"` 精确选择目标状态面板。
- 保留重新加载详情后 `detailError === ""` 与 `workflowApi.versions` 调用次数断言。

提交：`fix: target workflow detail error state in test`

## 验证纪律

本环境不执行用户本地 Node/Vitest/build 命令，因此本次改动不标记本地测试为已通过。用户应在 Windows 前端工作区执行 targeted test、全量 `npm test`、`npm run build` 与 `npm run test:gate`，并以实际终端结果作为验收事实。

建议验证顺序：

```powershell
npm test -- tests/api/workflows.test.ts tests/views/WorkflowLifecycle.test.ts tests/views/WorkflowLifecycleTriggerManagement.test.ts
npm test
npm run build
npm run test:gate
```

## 当前状态

- 最新 `main` 已同步到 `frontend`，当前 frontend 不落后 main。
- WorkflowLifecycle 生产状态清理修复：已提交。
- 生命周期测试契约修复：已提交。
- 详情错误 StatePanel 测试选择器修复：已提交。
- 回归文档：已同步。
- 本地最终验证：等待用户执行上述命令确认，当前不能标记为通过。
