# UI-03 / UI-04 Workflow 生命周期工作台迁移

## 状态

进行中：第二个核心页面 `WorkflowLifecycle` 完成第一批公共 UI 模式迁移。

## 范围

- 使用公共 `PageHeader` 统一页面标题、说明和刷新动作。
- 使用公共 `SurfaceCard` 统一工作流选择器、版本/发布、最近运行和触发调度信息容器。
- 使用公共 `StatePanel` 统一工作流列表的 Loading / Empty / Error / Permission 状态。
- 保留 Workflow → Version → Trigger / Scheduler → Execution → Runtime 的真实资源关联，不复制后端生命周期状态机。
- 保留现有 Runtime 深链参数：`execution_id`、`workflow_id`、`workflow_version_id`、`source`。
- 小屏幕下工作流选择区、生命周期步骤和详情卡片自动收缩为可读布局。

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

新增/更新 `frontend/tests/views/WorkflowLifecycle.test.ts`，覆盖：

1. 公共 PageHeader / SurfaceCard 模式；
2. 普通列表错误进入共享 Error 状态；
3. 403 进入共享 Permission 状态；
4. 真实 workflow/version/trigger/execution 生命周期数据；
5. Workflow 深链恢复；
6. Execution → Runtime 深链保持真实 ID；
7. 空列表中文状态。

远端 GitHub 环境不运行 Node/Vitest，因此不能将本轮门禁标记为已通过。

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