# UI-03 / UI-04 Workflow 生命周期工作台迁移

## 状态

进行中：第二个核心页面 `WorkflowLifecycle` 完成第一批公共 UI 模式迁移，并继续收敛异步列表状态、详情恢复与真实操作链路。

## 范围

- 使用公共 `PageHeader` 统一工作流生命周期标题、说明和刷新动作。
- 使用公共 `SurfaceCard` 统一工作流选择器、版本/发布、最近运行和触发调度信息容器。
- 使用公共 `StatePanel` 统一工作流列表的 Loading / Empty / Error / Permission 状态，以及详情请求失败状态。
- 保留 Workflow → Version → Trigger / Scheduler → Execution → Runtime 的真实资源关联，不复制后端生命周期状态机。
- 保留现有 Runtime 深链参数：`execution_id`、`workflow_id`、`workflow_version_id`、`source`。
- 小屏幕下工作流选择区、生命周期步骤和详情卡片自动收缩为可读布局。

## 本轮收敛：Trigger 真实写 Contract

后端 `main` 已确认存在完整的 Trigger 生命周期写入口，因此本轮前端不再把 Scheduled / Webhook Trigger 永久锁定为只读，而是仅消费已存在的真实 Contract：

- `PATCH /workflows/{workflow_id}/triggers/{trigger_id}`：支持 `name`、`status`、`config` 更新。
- Scheduled config 由后端 `ScheduledTriggerConfig` 校验：IANA timezone、60-86400 秒 interval、misfire policy、catch-up limit。
- Webhook config 支持 `event_id_field` 与可选的新 `secret`；后端只持久化 SHA-256 摘要，更新时未提交新 Secret 会保留原摘要，前端绝不读取或回显旧 Secret。
- `DELETE /workflows/{workflow_id}/triggers/{trigger_id}`：已存在真实删除 Contract，前端通过确认对话框闭环调用。
- `GET /workflows/{workflow_id}/triggers/{trigger_id}/schedule` 仍是 Scheduler 只读 Contract。
- 当前仍不存在 Scheduler 配置写 API，因此 Scheduler 修改继续保持只读，不在前端伪造接口。

### Scheduled Trigger 配置编辑

- 仅对 `scheduled` Trigger 显示“编辑配置”。
- 表单字段严格对应后端 Contract：`name`、`timezone`、`interval_seconds`、`misfire_policy`、`catch_up_limit`。
- `catch_up_limit` 仅在 `catch_up` 策略下可编辑；最终合法性仍由后端 422 Contract 裁决。
- 保存调用既有 `workflowApi.updateTrigger(...)`，成功后重新加载 Version / Trigger / Execution / Scheduler 数据，不在前端直接推算 `next_run_at`。
- 403 / 409 / 422 / 其他异常均有明确错误反馈。

### Webhook Trigger 配置编辑

- 仅对 `webhook` Trigger 显示“编辑配置”。
- 表单支持 `name`、`event_id_field` 与可选新 Secret。
- Secret 留空表示保持现有 Secret；前端不会把 `secret_hash` 当作可编辑值，也不会向 API 发送现有摘要。
- 后端返回的 `secret_configured` 仅用于事实展示，不构成 Secret 读取能力。
- 保存成功后重新读取 Trigger 数据，保证页面状态以服务端事实为准。

### Trigger 删除

- 删除必须经过 `ConfirmDialog`，明确提示删除的是 Trigger 入口，不删除既有 Execution / Trace / Audit Durable Facts。
- 提交期间禁止重复确认；成功后清理 delete target 并重新加载当前 Workflow 详情。
- 403 显示权限错误；409 显示后端运行时依赖/状态拒绝；其他异常显示删除失败。
- 取消确认不产生 DELETE 请求并清理 target，避免旧 Trigger 上下文残留。
- 归档 Workflow 在前端不提供编辑/删除入口；页面仍保持只读观测。

## 本轮收敛：实际操作链路

WorkflowLifecycle 不再只做生命周期只读观测，开始承载最小的真实运行闭环：

`已发布 Workflow → 启用 Manual Trigger → 确认 → invokeTrigger → 新 Execution → 刷新生命周期数据 → Runtime 诊断`

### 手动触发

- 仅对 `trigger_type === "manual"` 的触发器显示“立即运行”。
- 仅当 Workflow 已发布且 Trigger 为 `enabled` 时允许操作；草稿、归档或停用 Trigger 不在前端绕过后端约束执行。
- 使用共享 `ConfirmDialog` 明确告知本次以空 `input_data` 提交 Execution，避免无感知的写操作。
- 提交继续复用已有 `workflowApi.invokeTrigger(workflowId, triggerId, {})`，不新增 API client 或后端接口。
- 提交期间禁止重复确认；成功后清理 dialog target，并重新加载当前 Workflow 的 Version / Trigger / Execution / Scheduler 数据。
- 取消确认不会产生 API 写操作，并清理 dialog target，避免关闭后残留旧 Trigger 上下文。
- 403 / 409 / 422 / 其他异常均由明确反馈呈现，最终权限与业务状态仍由后端裁决。

### Execution 生命周期操作

- `pending`：允许 Run / Cancel；`running`：允许 Cancel；`failed`：允许 Retry / Resume；其他状态不提供生命周期变更按钮。
- 所有变更操作必须经过共享 `ConfirmDialog`，Cancel 使用危险样式。
- 提交期间禁止重复确认；成功后清理 Execution target / action，再重新读取后端 Execution 列表，不在前端直接修改状态。
- 取消确认不会调用任何生命周期 API，并清理 target / action，避免后续打开 dialog 时复用上一条 Execution。
- 403 明确提示权限不足；409 / 422 提示后端状态机拒绝并要求刷新；其他异常保留当前 dialog 上下文并提示失败，便于用户重新确认。
- Runtime / Trace / Audit 入口始终使用真实 Execution ID 和后端返回的 Workflow / Version ID。

## 之前已完成的状态收敛

### 列表空状态确定性

用户本地回归发现空列表文本已经出现，但共享 `StatePanel.state` 仍可能观察到 Loading。根因是页面状态与请求 loading 的推导存在异步窗口。

修复为显式 `PageState`：`loading | empty | error | permission | success`。空数组返回后立即进入 `empty`；正常列表详情完成后进入 `success`；403 与普通异常分别进入 `permission` / `error`。`loading` 仅负责请求期间反馈，不再作为其他页面状态的唯一来源。

### 详情失败状态统一

此前 `versions / triggers / listExecutions / schedule` 任一详情请求失败只通过 `ElMessage` 提示，页面主体仍可能保留成功态结构，无法提供稳定的恢复入口。

本轮将详情请求错误纳入独立 `detailError`：

- 详情加载开始时清除旧错误；
- 任一详情请求失败时清空可能过期的版本、触发器、Execution、Scheduler 数据，并显示共享 `StatePanel(state="error")`；
- 用户可直接点击“重新加载”重新请求当前真实 `workflow_id`；
- 详情失败不改变顶层 Workflow 列表的 `success` 状态，避免把资源列表错误误报成列表不可用。

## Contract / 安全边界

本轮不新增后端 API，也不新增前端平行 API client。Trigger 编辑/删除严格复用现有 `workflowApi.updateTrigger` / `workflowApi.deleteTrigger`；查询继续复用 `workflowApi.list`、`versions`、`triggers`、`schedule`、`listExecutions`；手动操作复用既有 `invokeTrigger`，Execution 操作复用既有 `runExecution` / `cancelExecution` / `retryExecution` / `resumeExecution`。Scheduler 没有 HTTP 写 Contract，因此仍保持只读。业务权限与状态机仍由后端最终裁决。

## 状态与操作契约

| 状态/阶段 | 用户反馈 | 恢复/下一步 |
| --- | --- | --- |
| Loading | 正在加载工作流 / 刷新按钮 loading | 等待请求完成 |
| Empty | 暂无工作流，并说明下一步 | 进入工作流创建流程 |
| Error | 工作流加载失败，提供通俗原因 | 重试 |
| Permission | 无权查看工作流 | 联系管理员 / 重试 |
| Success | 展示生命周期、真实版本、触发器和 Execution | Manual Trigger 可运行；Scheduled/Webhook 可编辑；Trigger 可删除；Execution 可进入 Runtime |
| Detail Error | 当前工作流详情加载失败，说明受影响数据并提供“重新加载” | 重新加载当前 workflow_id |
| Manual Trigger | 已发布 + enabled 时显示“立即运行” | ConfirmDialog → invokeTrigger → 刷新 Execution |
| Scheduled Trigger | 编辑真实 config | Form → updateTrigger → 刷新 Trigger / Scheduler |
| Webhook Trigger | 编辑 event_id / 可选新 Secret | Form → updateTrigger → 刷新 Trigger |
| Trigger Delete | 明确确认后删除 | ConfirmDialog → deleteTrigger → 刷新 Trigger / Scheduler |
| Scheduler | 展示真实 next/last run、lease、misfire 等状态 | 暂无写操作；等待后端 Scheduler write Contract |
| Execution Action | 按真实后端状态暴露 Run / Cancel / Retry / Resume | ConfirmDialog → 生命周期 API → 刷新 Execution |

## 测试

`frontend/tests/views/WorkflowLifecycle.test.ts` 覆盖原有生命周期、深链与 UI-05 确认行为。

新增 `frontend/tests/views/WorkflowLifecycleTriggerManagement.test.ts` 覆盖：

1. Scheduled Trigger 编辑器从真实 Trigger config 初始化；
2. Scheduled Trigger 使用真实 PATCH Contract 更新并刷新详情；
3. Webhook Trigger 更新时不读取、不回显、不发送现有 Secret；
4. Trigger 删除需要显式确认，取消不会写入；
5. Trigger 删除调用真实 DELETE Contract 并刷新详情。

远端 GitHub 环境不运行 Node/Vitest，因此本轮不虚报本地测试结果；用户本地验证结果以实际命令输出为准。

## 本地验证

```powershell
cd frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/WorkflowLifecycleTriggerManagement.test.ts
npm run build
```

## 下一步

继续保持 Scheduler 写操作只读边界。只有当后端提供并确认 Scheduler 配置修改、Trigger → Scheduler 同步、lease / misfire / idempotency 等完整 Write Contract 后，才进入前端 Scheduler 操作闭环；不在前端推导或伪造 Scheduler 状态。