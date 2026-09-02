# UI-05 WorkflowLifecycle Execution 操作与诊断闭环

## 目标

在 Workflow → Version → Trigger → Execution → Runtime 基础上，将 WorkflowLifecycle 的“最近运行”升级为真实多 Execution 运行记录，并建立稳定的：

**Execution → Runtime → Trace → Audit → WorkflowLifecycle**

双向诊断链。前端只传递后端已经存在的真实 ID，不推导 Trace / Audit 关系。

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

### 3. Trace / Audit → WorkflowLifecycle

Runtime correlation 查询以当前真实 `Trace ID` 或 `Audit ID` 为 focus，后端返回关联的真实 `Execution`。前端从该响应读取 `execution.id`、`workflow_id`、`workflow_version_id`，然后建立反向定位：

```text
Trace focus:
/workflows/lifecycle?workflow_id=<workflow_id>&execution_id=<execution_id>&trace_id=<trace_id>&source=runtime-correlation

Audit focus:
/workflows/lifecycle?workflow_id=<workflow_id>&execution_id=<execution_id>&audit_id=<audit_id>&source=runtime-correlation
```

规则：

1. `Trace ID` 必须来自后端 Trace Durable Fact 或当前 Trace focus URL；
2. `Audit ID` 必须来自后端 Audit Durable Fact 或当前 Audit focus URL；
3. `Execution ID` 必须来自后端 correlation response 的 `execution.id`；
4. `Workflow ID / Version ID` 必须来自后端 Execution correlation response；
5. 前端不得通过字符串、时间、索引、排序或其他启发式关系推导 ID；
6. WorkflowLifecycle 可以保留 `trace_id` / `audit_id` 作为诊断上下文，但选择 Execution 的依据仍是后端返回的真实 `execution.id`。

### 4. Execution / Trace / Audit 之间的继续导航

`RuntimeCorrelations` 提供：

- Execution → Execution 运行中心：携带真实 `execution_id`、`workflow_id`、`workflow_version_id`；
- Trace → Trace focus：携带真实 `trace_id`，并保留后端返回的 Execution / Workflow 上下文；
- Audit → Audit focus：携带真实 `audit.id`，并保留后端返回的 Execution / Workflow 上下文；
- Trace / Audit focus → WorkflowLifecycle：使用后端关联 Execution 建立反向定位，并保留当前诊断 ID。

因此完整路径为：

**WorkflowLifecycle → Execution → Trace → Audit → Execution → WorkflowLifecycle**

而不是由前端维护一套独立的关联图。

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
7. Runtime 支持从 Execution 上下文继续进入 Workflow 生命周期。
8. Runtime correlation 支持从 Trace / Audit focus 反向进入 WorkflowLifecycle，并保留原始诊断 ID。
9. 反向导航使用 `router.push`，保留浏览器历史中的诊断路径，便于逐级返回。

## API 边界

复用既有 API：

- `workflowApi.listExecutions(workflowId)`
- `workflowApi.runExecution(executionId)`
- `workflowApi.cancelExecution(executionId, reason?)`
- `workflowApi.retryExecution(executionId)`
- `workflowApi.resumeExecution(executionId)`
- `runtimeCorrelationsApi.execution(executionId)`
- `runtimeCorrelationsApi.trace(traceId)`
- `runtimeCorrelationsApi.audit(auditId)`

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
- Trace focus 查询使用真实 Trace ID；
- Audit focus 查询使用真实 Audit ID；
- Trace focus → WorkflowLifecycle 使用后端返回的真实 Execution ID，并保留 Trace ID；
- Audit focus → WorkflowLifecycle 使用后端返回的真实 Execution ID，并保留 Audit ID。

## 本地验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts
npm run build
```

> 本轮代码变更完成后，以本地 targeted test 与 build 结果作为最终验证依据；不要将远程静态审查结果冒充本地测试结果。

## 后续

继续围绕真实 Execution 事实推进诊断体验：优先把 WorkflowLifecycle 接收的 `trace_id` / `audit_id` 上下文用于反向诊断入口展示与继续跳转，但不复制后端关联规则，也不重新建设公共 UI 组件。
