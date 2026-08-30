# P1.1 深度交互与可观测性工作台

## 目标

本阶段将 P1 页面体验升级为真实运行上下文驱动的企业工作台：

- Runtime：页面级 Tab + Execution 按需加载；详情内部继续沿用现有 API，打开 Execution 后才加载时间线、Trace、Audit、Workflow 关系。
- Agent：调试上下文读取真实 Agent 列表与当前 published version，显示系统提示词、版本标识、模型，并把 Agent ID 带入 Runtime 诊断入口。
- Workflow：生命周期阶段由真实 Workflow / Execution 状态驱动；失败 Execution 提供 Retry / Resume，运行诊断直接携带 execution_id 与 workflow_id。

## 设计原则

1. **不复制 Backend Contract**：所有运行状态与生命周期操作通过现有 `runtimeApi` / `workflowApi`。
2. **按需加载**：Runtime 初次打开默认只加载健康概览；Execution 组件仅在用户进入运行中心或深链携带 execution_id/status 时挂载。
3. **深链保持上下文**：Runtime 使用 `execution_id`、`workflow_id`、`source` 等查询参数恢复诊断上下文。
4. **技术标识保留**：用户界面中文化，但 ID、状态值、错误代码仍保留真实后端标识。
5. **失败可恢复**：Workflow P1.1 只展示并调用已经存在的 run/cancel/retry/resume 生命周期接口，不新增并行状态机。

## Runtime

### Tab

```text
运行健康 | Execution 运行中心 | 诊断路径
```

默认无深链时进入运行健康；存在 `execution_id` 或 `status` 时直接进入 Execution。

### 数据加载边界

| 页面阶段 | 请求 |
| --- | --- |
| 运行健康 | `/runtime/executions` 最近窗口 |
| Execution 列表 | `/runtime/executions` 分页 |
| Execution 详情 | `/runtime/executions/{id}` |
| 时间线 | `/runtime/executions/{id}/events` |
| Trace | `/runtime/executions/{id}/trace` |
| Audit | `/runtime/audit-logs` |
| Workflow 关系 | `/workflows/executions/{id}` + `/workflows/{workflow_id}/executions` |

## Agent

调试上下文加载：

```text
/agents
  ↓
选择 Agent
  ↓
/agents/{id}/published-version
  ↓
Published Version
  ├── version
  ├── version id
  ├── model id
  └── system prompt
```

Runtime 入口携带 `agent_id`，避免从 Execution 中猜测 Agent。

## Workflow

```text
Workflow status
      ↓
版本 / 发布
      ↓
最近 Execution
 ┌────┼──────────┐
 pending running failed
   │      │       ├── Retry
   │      ├──Cancel└── Resume
   └──Run
      ↓
 Runtime Execution
      ↓
 Trace → Audit
```

Execution 状态以后端 `WorkflowExecution.status` 为准；前端不推断隐藏状态。

## 验收

本阶段代码完成后必须执行：

```powershell
cd frontend
npm test
npm run build
```

重点回归：

- Runtime：空状态、状态筛选、Execution 深链、Retry / Resume、Trace / Audit。
- Agent：发布版本加载、中文化、系统提示词、调试 Runtime 跳转、错误降级。
- Workflow：生命周期状态、真实 Execution、Retry / Resume / Cancel、Runtime 深链。

在本地测试尚未实际执行前，不将本阶段标记为“测试通过”。
