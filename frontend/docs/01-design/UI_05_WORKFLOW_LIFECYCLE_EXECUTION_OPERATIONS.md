# UI-05 WorkflowLifecycle Execution 操作闭环

## 目标

在已完成的 Workflow → Version → Trigger → Execution → Runtime 观测链路上，继续收敛 Execution 的最小可操作闭环。前端只依据后端返回的 `execution.status` 决定可见操作，不复制后端状态机。

## 操作矩阵

| Execution 状态 | 前端操作 | API |
| --- | --- | --- |
| `pending` | 运行、取消 | `runExecution` / `cancelExecution` |
| `running` | 取消 | `cancelExecution` |
| `failed` | 重试、恢复 | `retryExecution` / `resumeExecution` |
| `completed` | Runtime 诊断 | Runtime deep link |
| `cancelled` | Runtime 诊断 | Runtime deep link |
| 其他未知状态 | 不显示生命周期操作 | 后端最终裁决 |

## 交互规则

1. 运行、取消、重试、恢复全部经过 `ConfirmDialog`，避免误操作。
2. 操作提交期间按钮进入 loading，防止同一 Execution 被重复提交。
3. 操作成功后重新加载当前 Workflow 的 Execution 列表，以服务端最终状态刷新 UI。
4. 403 显示权限失败；409 / 422 等业务冲突不在前端推断原因，只给出可恢复提示。
5. 失败操作不改变本地 Execution 状态，避免前端先行伪造状态机。
6. Runtime 入口继续携带真实 `execution_id`、`workflow_id`、`workflow_version_id`。
7. `failed` 同时提供 Retry / Resume，是两个不同的后端语义，不在 UI 层合并为一个“继续”。

## 真实 API 边界

复用 `frontend/src/api/workflows.ts` 已存在的：

- `runExecution(executionId)`
- `cancelExecution(executionId, reason?)`
- `retryExecution(executionId)`
- `resumeExecution(executionId)`
- `execution(executionId)` / `listExecutions(workflowId)`

本轮不新增 API，不修改后端执行状态定义。

## 测试

`WorkflowLifecycle.test.ts` 覆盖：

- pending 只显示 Run / Cancel；
- running 只显示 Cancel；
- failed 显示 Retry / Resume；
- 调用真实 API client 对应方法；
- 操作完成后重新拉取 Execution；
- Runtime 深链保留真实 Execution 上下文。

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

## 后续

下一步仍在 WorkflowLifecycle 内推进：将多 Execution 列表从“最近一条摘要”扩展成可定位的运行记录，并在不重复公共组件的前提下继续强化 Runtime / Trace / Audit 诊断上下文。
