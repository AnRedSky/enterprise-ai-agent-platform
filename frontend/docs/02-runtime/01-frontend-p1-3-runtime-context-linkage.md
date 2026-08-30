# P1.3 Runtime 深链接上下文联动

## 目标

把 Agent 调试、Workflow 生命周期与 Runtime Execution 运行中心之间已有的真实上下文参数变成可用的深链接体验。进入 `/runtime` 时，只要 URL 携带任一运行上下文，就直接打开 Execution Tab，并保留现有按需加载策略。

## Contract 对齐

本切片不新增后端接口，也不在前端推断运行状态。Runtime Execution 页面已有正式筛选上下文：

- `execution_id`
- `status`
- `agent_id`
- `workflow_id`
- `trace_id`
- `request_id`

同时保留 `source` 作为来源上下文标识，例如 Agent Debug、Workflow Trigger、Runtime Relation。

## 实现决策

1. `RuntimeWorkspaceTabs` 使用统一 `runtimeContextKeys` 判断深链接是否具备运行上下文。
2. 任一上下文存在时自动激活 `Execution 运行中心` 并挂载 `RuntimeExecutions`，避免用户先看到 Overview 再手工切 Tab。
3. 监听路由 query 变化，支持浏览器前进/后退以及页面内导航后重新同步 Tab 状态。
4. 无运行上下文时继续默认 Overview，并保持 Execution 按需挂载，避免无意义请求。
5. 不复制或改写 RuntimeExecutions 的筛选逻辑；上下文仍由后端真实 Execution 数据驱动。

## 自动化测试

新增 `tests/views/RuntimeWorkspaceTabs.test.ts`，覆盖：

- Agent Debug `agent_id` 深链接；
- Workflow / Trace 深链接；
- 无上下文默认 Overview。

## 本地验证

当前用户反馈的 `vitest/config`、`@vitejs/plugin-vue`、`vitest` 无法解析，根因是 `frontend/node_modules` 未完成安装，而不是 `WorkflowLifecycle.test.ts` 本身的断言失败。`package.json` 已声明 `vitest ^4.1.10`、`@vitejs/plugin-vue ^5.2.1` 等开发依赖，因此本地应先执行：

```powershell
cd frontend
npm ci
npm test -- --run tests/views/RuntimeWorkspaceTabs.test.ts tests/views/Runtime.test.ts tests/views/WorkflowLifecycle.test.ts
npm run build
```

本轮无法替代用户本机执行上述命令，因此不预填测试通过结果。

## 后续计划

- P1.4：Workflow Lifecycle 的 Execution 行点击直接进入 Runtime，并在 Runtime 中回显来源 Workflow。
- P1.5：Agent Debug 在对话完成后提供 Execution / Trace 快速入口，并展示真实执行摘要。
- P2：Runtime Tab 状态持久化、实时刷新、失败聚合、SLO/告警摘要与事件流。
