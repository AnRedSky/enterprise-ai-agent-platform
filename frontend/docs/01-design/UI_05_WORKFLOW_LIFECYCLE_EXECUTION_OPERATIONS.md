# UI-05 WorkflowLifecycle Execution 操作与诊断闭环

## 目标

在 Workflow → Version → Trigger → Execution → Runtime 基础上，将 WorkflowLifecycle 的“最近运行”升级为真实多 Execution 运行记录，并建立稳定的：

**Execution → Runtime → Trace → Audit → WorkflowLifecycle**

双向诊断链。前端只传递后端已经存在的真实 ID，不推导 Trace / Audit 关系。

## Execution 运行记录

`workflowApi.listExecutions(workflowId)` 返回的全部 Execution 记录直接作为当前 Workflow 的运行记录源。页面不再只展示 `executions[0]` 摘要。

每条记录展示 Execution ID、后端状态、创建时间、当前节点、错误信息、Retry / Resume 来源以及生命周期和诊断入口。

## Execution 定位

`execution_id` 作为 WorkflowLifecycle 的可复现定位上下文。进入页面时，如果该 ID 属于当前 Workflow 的真实 `listExecutions` 结果，则自动定位该记录；否则回退到最新记录。

## 诊断上下文

WorkflowLifecycle 接收 Runtime correlation 反向导航携带的：

- `execution_id`：真实 Execution 根上下文；
- `trace_id`：当前真实 Trace focus；
- `audit_id`：当前真实 Audit focus。

当 `trace_id` 或 `audit_id` 存在时，页面展示“反向诊断上下文”，同时显示 Execution、Workflow、Workflow Version 和诊断 ID，并提供继续诊断入口。

继续诊断时，将同一组真实 ID 返回 Runtime correlations：

```text
Trace: focus_type=trace, focus_id=<trace_id>
Audit: focus_type=audit, focus_id=<audit_id>
两者均保留 execution_id + workflow_id + workflow_version_id
```

切换到另一条 Execution 或主动清除上下文时，旧 Trace/Audit ID 必须清除，避免跨 Execution 污染诊断上下文。

## 诊断链路

### Execution → Runtime

携带 `execution_id`、`workflow_id`、`workflow_version_id`。

### Execution → Trace / Audit

进入 Runtime `correlations` Tab 时以 Execution 为 focus root。Trace ID、Audit ID 及 Operator Action 关系由后端关联 Contract 返回。

### Trace / Audit → WorkflowLifecycle

Runtime correlation 查询以真实 Trace ID 或 Audit ID 为 focus，后端返回关联的真实 Execution。前端读取 response 中的 `execution.id`、`workflow_id`、`workflow_version_id`，进入 WorkflowLifecycle 时保留当前 `trace_id` / `audit_id`。

### WorkflowLifecycle → Trace / Audit（上下文续接）

WorkflowLifecycle 不重新查询或推导关联关系；它只把当前页面已有的真实诊断上下文原样透传回 Runtime correlation，并允许用户清除该上下文。

因此完整路径为：

**WorkflowLifecycle → Execution → Trace → Audit → Execution → WorkflowLifecycle → Trace / Audit**

## 约束

1. Execution ID 必须来自后端 Execution Durable Fact。
2. Trace ID 必须来自后端 Trace Durable Fact 或当前 Trace focus URL。
3. Audit ID 必须来自后端 Audit Durable Fact 或当前 Audit focus URL。
4. Workflow ID / Version ID 必须来自后端 Execution correlation response。
5. 前端不得通过字符串、时间、索引、排序或启发式规则推导关系。
6. WorkflowLifecycle 接收诊断上下文只负责展示与透传，不负责建立新的关联图。
7. 切换 Execution 时清除旧诊断上下文。
8. 清除上下文只影响 URL 与页面焦点，不修改任何服务端事实。

## API 边界

复用既有 API，不新增后端接口：

- `workflowApi.listExecutions(workflowId)`
- `runtimeCorrelationsApi.execution(executionId)`
- `runtimeCorrelationsApi.trace(traceId)`
- `runtimeCorrelationsApi.audit(auditId)`

## Regression Test

`WorkflowLifecycle.test.ts` 覆盖：

- `execution_id + trace_id` 深链恢复；
- `execution_id + audit_id` 深链恢复；
- Trace 上下文继续返回 Runtime 时保持真实 Execution / Trace ID；
- Audit 上下文继续返回 Runtime 时保持真实 Execution / Audit ID；
- 清除上下文不改变当前 Execution；
- 切换 Execution 后不会携带旧 Trace/Audit ID。

`RuntimeCorrelations.test.ts` 覆盖 Trace / Audit focus → WorkflowLifecycle 的反向定位。

## 本地验证

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts
npm run build
```

本轮仍采用：**实现 → targeted test → 文档 → 原子提交**。

## 下一步

进入下一层 **Trace / Audit 具体事实定位**：优先基于后端返回的真实 Trace / Audit Durable Facts 建立具体记录定位，不在前端复制关联规则或虚构 ID。