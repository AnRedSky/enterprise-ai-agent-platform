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

## 本轮收敛：实际操作链路

WorkflowLifecycle 不再只做生命周期只读观测，开始承载最小的真实运行闭环：

`已发布 Workflow → 启用 Manual Trigger → 确认 → invokeTrigger → 新 Execution → 刷新生命周期数据 → Runtime 诊断`

### 手动触发

- 仅对 `trigger_type === "manual"` 的触发器显示“立即运行”。
- 仅当 Workflow 已发布且 Trigger 为 `enabled` 时允许操作；草稿、归档或停用 Trigger 不在前端绕过后端约束执行。
- 使用共享 `ConfirmDialog` 明确告知本次以空 `input_data` 提交 Execution，避免无感知的写操作。
- 提交继续复用已有 `workflowApi.invokeTrigger(workflowId, triggerId, {})`，不新增 API client 或后端接口。
- 成功后立即重新加载当前 Workflow 的 Version / Trigger / Execution / Scheduler 数据，使生命周期阶段和最近运行保持真实后端状态。
- 403 显示权限错误，其他异常提示提交失败；最终权限与业务状态仍由后端裁决。

该实现只收敛 WorkflowLifecycle 的实际操作入口，不重新实施已经完成的 UI-03 / UI-04 公共组件迁移，也不把后端 Workflow 状态机复制到前端。

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

本轮不新增后端 API，不修改生命周期状态定义。查询继续复用 `workflowApi.list`、`versions`、`triggers`、`schedule`、`listExecutions`；手动操作复用既有 `invokeTrigger`。403 仅用于页面 Permission / 操作错误展示；业务权限仍由后端最终裁决。

## 状态与操作契约

| 状态/阶段 | 用户反馈 | 恢复/下一步 |
| --- | --- | --- |
| Loading | 正在加载工作流 / 刷新按钮 loading | 等待请求完成 |
| Empty | 暂无工作流，并说明下一步 | 进入工作流创建流程 |
| Error | 工作流加载失败，提供通俗原因 | 重试 |
| Permission | 无权查看工作流 | 联系管理员 / 重试 |
| Success | 展示生命周期、真实版本、触发器和 Execution | 手动 Trigger 可提交运行；Execution 可进入 Runtime |
| Detail Error | 当前工作流详情加载失败，说明受影响数据并提供“重新加载” | 重新加载当前 workflow_id |
| Manual Trigger | 已发布 + enabled 时显示“立即运行” | ConfirmDialog → invokeTrigger → 刷新 Execution |

## 测试

`frontend/tests/views/WorkflowLifecycle.test.ts` 覆盖：

1. 公共 PageHeader / SurfaceCard 模式；
2. 普通列表错误进入共享 Error 状态；
3. 403 进入共享 Permission 状态；
4. 真实 workflow/version/trigger/execution 生命周期数据；
5. Workflow 深链恢复；
6. Execution → Runtime 深链保持真实 ID；
7. 空列表中文状态及 `StatePanel.state === "empty"` 契约；
8. 详情请求失败进入共享 Error 状态并可重新加载；
9. Manual Trigger 经过确认后调用真实 `invokeTrigger`，并重新加载 Execution。

远端 GitHub 环境不运行 Node/Vitest，因此本轮代码提交前不虚报本地测试结果；用户本地验证结果以实际命令输出为准。

## 本地验证

```powershell
cd frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/components/ConfirmDialog.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 下一步

继续围绕同一核心页面收敛 Execution 操作闭环：基于真实 Execution 状态提供 `pending / running / failed / cancelled` 的合法操作入口，并统一进入 Runtime 的诊断上下文；不重复 UI-03 / UI-04 公共模式迁移，不复制后端状态机。
