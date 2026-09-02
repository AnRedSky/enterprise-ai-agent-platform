# UI-03 / UI-04 Workflow 生命周期工作台迁移

## 状态

进行中：第二个核心页面 `WorkflowLifecycle` 完成第一批公共 UI 模式迁移，并继续收敛异步列表状态与详情交互状态。

## 范围

- 使用公共 `PageHeader` 统一工作流生命周期标题、说明和刷新动作。
- 使用公共 `SurfaceCard` 统一工作流选择器、版本/发布、最近运行和触发调度信息容器。
- 使用公共 `StatePanel` 统一工作流列表的 Loading / Empty / Error / Permission 状态，以及详情请求失败状态。
- 保留 Workflow → Version → Trigger / Scheduler → Execution → Runtime 的真实资源关联，不复制后端生命周期状态机。
- 保留现有 Runtime 深链参数：`execution_id`、`workflow_id`、`workflow_version_id`、`source`。
- 小屏幕下工作流选择区、生命周期步骤和详情卡片自动收缩为可读布局。

## 本轮修复

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

该状态仍是前端展示层状态，不复制 Workflow 后端生命周期状态机，也不新增 API。

## Contract / 安全边界

本次不新增后端 API，不修改生命周期状态定义。继续复用 `workflowApi.list`、`versions`、`triggers`、`schedule`、`listExecutions`。403 仅用于页面 Permission 展示；业务权限仍由后端最终裁决。

## 状态契约

| 状态 | 用户反馈 | 恢复动作 |
| --- | --- | --- |
| Loading | 正在加载工作流 / 刷新按钮 loading | 等待请求完成 |
| Empty | 暂无工作流，并说明下一步 | 进入工作流创建流程 |
| Error | 工作流加载失败，提供通俗原因 | 重试 |
| Permission | 无权查看工作流 | 联系管理员 / 重试 |
| Success | 展示生命周期、真实版本、触发器和 Execution | 进入 Runtime 诊断 |
| Detail Error | 当前工作流详情加载失败，说明受影响数据并提供“重新加载” | 重新加载当前 workflow_id |

## 测试

`frontend/tests/views/WorkflowLifecycle.test.ts` 覆盖：

1. 公共 PageHeader / SurfaceCard 模式；
2. 普通列表错误进入共享 Error 状态；
3. 403 进入共享 Permission 状态；
4. 真实 workflow/version/trigger/execution 生命周期数据；
5. Workflow 深链恢复；
6. Execution → Runtime 深链保持真实 ID；
7. 空列表中文状态及 `StatePanel.state === "empty"` 契约；
8. 详情请求失败进入共享 Error 状态并可重新加载。

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

## 已知限制

本轮只收敛 WorkflowLifecycle 的详情异步状态和恢复交互，不重构已有 Workflow 创建/编辑业务链路，不新增并行 Dialog、状态机或 API client。后续继续以“一个核心页面 → 公共模式 → targeted test → 文档 → 原子提交”推进 UI-05。
