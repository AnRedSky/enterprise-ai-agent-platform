# UI-05 WorkflowLifecycle Execution 操作与诊断闭环

## 目标

在 Workflow → Version → Trigger → Execution → Runtime 基础上，将 WorkflowLifecycle 的“最近运行”升级为真实多 Execution 运行记录，并建立稳定的：

**Execution → Runtime → Trace → Audit**

诊断入口。前端只传递后端已经存在的真实 ID，不推导 Trace / Audit 关系。

## Execution 运行记录

`workflowApi.listExecutions(workflowId)` 返回的全部 Execution 记录直接作为当前 Workflow 的运行记录源。页面不再只展示 `executions[0]` 摘要。

每条记录展示：

- Execution ID；
- 后端 `status`；
- `created_at`；
- `current_node_id`；
- `error_code`；
- Retry / Resume 来源字段（存在时）；
- 生命周期操作；
- 定位、Runtime、Trace / Audit 入口。

## Execution 定位

`execution_id` 作为 WorkflowLifecycle 的可复现定位上下文：

```text
/workflows/lifecycle?workflow_id=<workflow_id>&execution_id=<execution_id>&source=workflow-lifecycle
```

进入页面时，如果该 ID 属于当前 Workflow 的真实 `listExecutions` 结果，则自动定位该记录；否则回退到最新记录。

“定位”只更新 URL 上下文和当前焦点，不修改服务端状态。

## 诊断链路

### 1. Execution → Runtime

携带：

- `execution_id`
- `workflow_id`
- `workflow_version_id`
- `source=workflow-lifecycle`

Runtime 以 `execution_id` 加载真实运行详情、Timeline 与 Trace。

### 2. Execution → Trace / Audit

进入 Runtime `correlations` Tab 时携带：

- `focus_type=execution`
- `focus_id=<execution_id>`
- `execution_id=<execution_id>`
- `workflow_id`
- `workflow_version_id`

`RuntimeCorrelations` 从 URL 恢复 Execution focus，并调用现有 `runtimeCorrelationsApi.execution(executionId)`。Trace ID、Audit ID 及 Operator Action 关系全部由后端关联 Contract 返回。

## 操作矩阵

| Execution 状态 | 前端操作 | API |
| --- | --- | --- |
| `pending` | 运行、取消 | `runExecution` / `cancelExecution` |
| `running` | 取消 | `cancelExecution` |
| `failed` | 重试、恢复 | `retryExecution` / `resumeExecution` |
| `completed` | 诊断 | Runtime / Trace / Audit |
| `cancelled` | 诊断 | Runtime / Trace / Audit |
| 其他未知状态 | 不显示生命周期操作 | 后端最终裁决 |

## 交互规则

1. 生命周期变更操作继续经过 `ConfirmDialog`。
2. 操作成功后重新拉取当前 Workflow 的 Execution 列表，以服务端最终状态刷新 UI。
3. 403 显示权限失败；409 / 422 显示状态冲突恢复提示。
4. 不在前端复制 Execution 状态机，也不根据 Retry / Resume ID 自行制造父子关系。
5. Execution 定位、Runtime、Trace、Audit 都使用真实 Execution ID。
6. Trace / Audit 的具体关联 ID 只接受后端 Durable Facts，不从 Execution ID 字符串或时间等信息推断。
7. Runtime 仍支持从 Execution 上下文继续进入 Workflow 生命周期，保持双向导航基础。

## API 边界

复用既有 API：

- `workflowApi.listExecutions(workflowId)`
- `workflowApi.runExecution(executionId)`
- `workflowApi.cancelExecution(executionId, reason?)`
- `workflowApi.retryExecution(executionId)`
- `workflowApi.resumeExecution(executionId)`
- `runtimeCorrelationsApi.execution(executionId)`

本轮不新增后端接口。

## Regression Test

`WorkflowLifecycle.test.ts` 覆盖：

- 多 Execution 数据被展示并支持指定 `execution_id` 定位；
- 定位只更新真实 Workflow / Execution URL 上下文；
- Runtime 深链携带 Execution / Workflow / Version ID；
- Trace / Audit 深链以 Execution 为关联根；
- 原有 pending / running / failed 生命周期操作不回归。

`RuntimeCorrelations.test.ts` 覆盖：

- 从 URL 恢复 `focus_type=execution` / `focus_id=execution_id`；
- 关联查询直接调用后端 Execution correlation Contract。

## 本地验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts
npm run build
```

> 当前环境只能完成远程代码实现与静态审查；未宣称本轮本地测试已通过，以上命令用于本地最终验证。

## 后续

继续围绕真实 Execution 事实推进诊断体验：优先完善 Runtime 中从 Execution → Trace → Audit 的反向定位与返回 WorkflowLifecycle，不重新建设公共 UI 组件，也不复制后端关联规则。
