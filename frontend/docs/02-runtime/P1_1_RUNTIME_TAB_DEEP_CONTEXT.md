# P1.1 Runtime 工作台：深链 Tab 与诊断上下文

## 1. 本轮目标

在既有 Runtime 可观测性工作台基础上，补齐“深链可恢复 + Tab 可分享 + 上下文不丢失”的交互闭环，不复制后端状态机，也不提前请求重型诊断数据。

## 2. 实现范围

- Runtime Tab 支持通过 `tab=overview|executions|diagnostics` 深链恢复当前视图。
- 已存在 `execution_id`、`workflow_id`、`agent_id`、`trace_id`、`request_id` 等 Runtime 上下文时，默认进入 Execution 运行中心。
- Tab 切换通过路由持久化，并保留原有 Runtime 上下文参数，避免 Agent Debug / Workflow 链路在页面切换时丢失。
- 诊断页展示当前深链携带的技术上下文，仅用于定位，不作为业务事实来源。
- Execution 组件仍保持按需挂载：只有进入 Execution Tab 或携带 Runtime 上下文时才挂载。

## 3. Contract 对齐

当前前端 Runtime API 已提供 Execution、Event、Workflow Trace、Audit 等正式查询能力；Workflow API 已提供 WorkflowExecution、节点、Trace 及生命周期操作。本轮只增强路由和信息架构，没有新增后端 Endpoint 或前端平行状态机。

## 4. 设计决策

| 决策 | 原因 |
|---|---|
| `tab` 作为可选路由上下文 | 支持刷新、分享和浏览器前进/后退恢复工作区 |
| 保留所有已知 Runtime context keys | 防止从 Agent Debug / Workflow 进入 Runtime 后上下文丢失 |
| 未知 `tab` 回退到既有默认策略 | 避免错误 URL 导致空白页面 |
| 诊断上下文只读 | 技术 ID 是诊断定位信息，不应在 UI 层修改业务事实 |
| 不在 Overview 首次请求 Trace/Audit | 遵循 Runtime 按需加载原则，降低首屏负载 |

## 5. 测试覆盖

新增/更新 `frontend/tests/views/RuntimeWorkspaceTabs.test.ts`，覆盖：

- Agent Debug 深链进入 Execution；
- Workflow / Trace 深链进入 Execution；
- Diagnostics 深链恢复并展示上下文；
- 无上下文时默认 Overview；
- Tab 切换后 Runtime 上下文仍被保留。

## 6. 本地验收

当前环境无法直接执行本地 Node 测试：容器无法解析 `github.com`，无法获取仓库工作树与安装依赖。因此本轮不将本地测试标记为通过。

在开发机执行：

```powershell
cd frontend
npm ci
npm test -- tests/views/RuntimeWorkspaceTabs.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

其中 `npm ci` 是针对此前 `npx vitest` 报 `vitest` / `@vitejs/plugin-vue` 缺失的正确修复路径；不得使用 `npx` 临时下载依赖代替项目依赖安装。

## 7. 下一步

1. Agent 对话调试继续补齐真实会话 / request / execution 上下文回流。
2. Workflow 生命周期页将选中的 `WorkflowExecution` 与 Runtime Execution 详情建立真实 ID 联动。
3. Runtime 详情继续拆分 Timeline / Trace / Audit 的按需加载和失败恢复。
4. 完成上述闭环后再推进 Provider / Health / Alert / Notification / Metrics 前端化。
