# UI-03 / UI-04 Workflow 生命周期工作台迁移

## 状态

进行中：第二个核心页面 `WorkflowLifecycle` 完成第一批公共 UI 模式迁移，并继续收敛异步列表状态的确定性转换。

## 范围

- 使用公共 `PageHeader` 统一页面标题、说明和刷新动作。
- 使用公共 `SurfaceCard` 统一工作流选择器、版本/发布、最近运行和触发调度信息容器。
- 使用公共 `StatePanel` 统一工作流列表的 Loading / Empty / Error / Permission 状态。
- 保留 Workflow → Version → Trigger / Scheduler → Execution → Runtime 的真实资源关联，不复制后端生命周期状态机。
- 保留现有 Runtime 深链参数：`execution_id`、`workflow_id`、`workflow_version_id`、`source`。
- 小屏幕下工作流选择区、生命周期步骤和详情卡片自动收缩为可读布局。

## 本轮修复

### 问题

用户本地 `tests/views/WorkflowLifecycle.test.ts` 的空列表用例出现：

```text
Expected: "empty"
Received: "loading"
```

同时页面文本已经出现“暂无工作流”。这说明空状态文案已经可见，但测试观察到的共享 `StatePanel.state` 仍可能停留在 Loading 状态。

### 根因

页面状态此前通过 `permissionDenied`、`error`、`loading` 和列表数据组合计算。空列表路径虽然已经提前返回，但 Empty 状态仍间接依赖统一 `finally` 对 `loading` 的关闭，状态转换与组件更新之间存在不必要的异步窗口。

### 修复

- 引入仅用于视图呈现的 `PageState`：`loading | empty | error | permission | success`。
- `load()` 开始时明确进入 `loading`。
- `workflowApi.list()` 返回空数组后立即将 `pageState` 设置为 `empty`，并清空 `selectedId`，不进入详情加载。
- 正常非空列表在详情加载完成后进入 `success`。
- 403 明确进入 `permission`，其他列表异常进入 `error`。
- `loading` 仅负责刷新按钮和请求期间反馈，不再作为 Empty / Error / Permission 的唯一状态推导来源。
- `detailLoading` 继续独立管理 Version / Trigger / Scheduler / Execution 详情请求。

该 `PageState` 只描述前端页面呈现状态，不复制 Workflow 后端生命周期状态机；不新增 API，也不改变已有 Workflow / Runtime 深链行为。

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

## 测试

`frontend/tests/views/WorkflowLifecycle.test.ts` 覆盖：

1. 公共 PageHeader / SurfaceCard 模式；
2. 普通列表错误进入共享 Error 状态；
3. 403 进入共享 Permission 状态；
4. 真实 workflow/version/trigger/execution 生命周期数据；
5. Workflow 深链恢复；
6. Execution → Runtime 深链保持真实 ID；
7. 空列表中文状态及 `StatePanel.state === "empty"` 契约。

远端 GitHub 环境不运行 Node/Vitest，因此本轮修复后的测试结果必须由用户本地环境执行确认，不能将未执行的门禁标记为通过。

## 本地验证

```powershell
cd frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 已知限制

本轮只收敛公共页面状态与容器模式，不重构已有 Workflow 创建/编辑业务链路，也不新增并行 Dialog、状态机或 API client。
