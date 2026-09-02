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

## Trace / Audit 具体事实定位

Runtime correlations 的列表记录直接映射后端 `WorkflowTraceEvent` / `AuditLog` Durable Facts。前端不得从事件时间、索引或字符串自行拼装诊断事实。

### Trace 事实

选中具体 Trace 记录后展示后端返回的：

- Trace ID；
- Execution ID；
- Workflow ID / Workflow Version ID；
- Event Type；
- Node ID；
- Actor ID；
- Status；
- Error Code / Error Message；
- Data JSON；
- Created At。

Trace 具体事实可直接返回 WorkflowLifecycle，使用该记录自身的真实 Trace ID 和 Execution / Workflow / Version 上下文，而不是依赖当前查询根的 `focus_id`。

### Audit 事实

选中具体 Audit 记录后展示后端返回的：

- Audit ID；
- Action；
- Execution ID；
- Workflow ID / Workflow Version ID；
- Trace ID；
- Actor ID；
- Resource Type / Resource ID；
- Request ID；
- Status；
- Error Code；
- Metadata；
- Created At。

Audit 具体事实可直接返回 WorkflowLifecycle，使用该记录自身的真实 Audit ID 和 Execution / Workflow / Version 上下文。

如果 Audit Durable Fact 自带真实 `trace_id`，允许继续进入 Trace focus；没有 `trace_id` 时不创建任何推导关系。

### 深链与分页边界

列表 `traces.items` / `audits.items` 仍严格遵循分页参数，只表达当前列表页。**深链目标不再依赖目标必须落在当前分页页内。** 后端 Runtime correlation Contract 已补充 focused-record 语义：

- `/runtime/correlations/traces/{trace_id}` 返回 `focused_traces`，按当前 tenant + 精确 `trace_id` 查询全部匹配的 Trace Durable Facts，不受 `trace_page` / `trace_page_size` 影响；
- `/runtime/correlations/audits/{audit_id}` 返回 `focused_audit`，按当前 tenant + 精确 `audit_id` 查询目标 Audit Durable Fact，不受 `audit_page` / `audit_page_size` 影响；
- Audit 自带 `trace_id` 时，同时返回对应 `focused_traces`；
- Trace ID 如果对应多个 Trace Event，则返回全部匹配 Durable Facts，禁止通过时间、排序、索引或“第一条”猜测单一事实；
- 目标不存在或不属于当前 tenant 时，仍由既有 404 / 关联解析 Contract 处理；Trace 映射多个 Execution 时保持 409 歧义保护。

因此前端不得扩大分页，也不得为了补齐深链目标重新复制后端关联查询。

## 诊断链路

### Execution → Runtime

携带 `execution_id`、`workflow_id`、`workflow_version_id`。

### Execution → Trace / Audit

进入 Runtime `correlations` Tab 时以 Execution 为 focus root。Trace ID、Audit ID 及 Operator Action 关系由后端关联 Contract 返回。

### Trace / Audit → WorkflowLifecycle

Runtime correlation 查询以真实 Trace ID 或 Audit ID 为 focus，后端返回关联的真实 Execution。前端读取 response 中的 `execution.id`、`workflow_id`、`workflow_version_id`，进入 WorkflowLifecycle 时保留当前 `trace_id` / `audit_id`。

### 具体 Trace / Audit → WorkflowLifecycle

从列表中选择具体 Durable Fact 时，回退导航必须使用该行本身携带的真实 `trace_id` / `audit_id`。对于分页外的深链目标，前端应使用后端 focused-record Contract 提供的 Durable Fact，不得通过分页扩大或关系推导获得目标。

### Audit → Trace

Audit 记录只有在后端提供 `trace_id` 时才显示 Trace 定位入口；该入口直接以真实 Trace ID 进入 Runtime correlation，不做字符串或时间推导。

### WorkflowLifecycle → Trace / Audit（上下文续接）

WorkflowLifecycle 不重新查询或推导关联关系；它只把当前页面已有的真实诊断上下文原样透传回 Runtime correlation，并允许用户清除该上下文。

因此完整路径为：

**WorkflowLifecycle → Execution → Trace → Audit → Trace → Execution → WorkflowLifecycle → Trace / Audit**

## 约束

1. Execution ID 必须来自后端 Execution Durable Fact。
2. Trace ID 必须来自后端 Trace Durable Fact 或当前 Trace focus URL。
3. Audit ID 必须来自后端 Audit Durable Fact 或当前 Audit focus URL。
4. Workflow ID / Version ID 必须来自后端 Execution correlation response 或具体 Durable Fact。
5. 前端不得通过字符串、时间、索引、排序或启发式规则推导关系。
6. WorkflowLifecycle 接收诊断上下文只负责展示与透传，不负责建立新的关联图。
7. 具体事实返回 WorkflowLifecycle 时，优先使用选中记录本身的真实 ID，而不是页面当前 focus ID。
8. Audit → Trace 仅允许使用后端返回的 `trace_id`。
9. 切换 Execution 时清除旧诊断上下文。
10. 清除上下文只影响 URL 与页面焦点，不修改任何服务端事实。
11. 具体 Trace/Audit 面板只展示后端已经返回的 Durable Fact 字段。
12. 深链目标跨分页时只允许消费后端 `focused_traces` / `focused_audit`，禁止前端扩大分页或复制关联 SQL 逻辑。

## API 边界

Runtime correlation API 保持既有四个入口，不新增额外查询接口：

- `runtimeCorrelationsApi.execution(executionId)`
- `runtimeCorrelationsApi.trace(traceId)`
- `runtimeCorrelationsApi.audit(auditId)`
- `runtimeCorrelationsApi.operatorAction(operatorActionId)`

Response 在既有分页集合之外新增：

- `focused_traces: WorkflowTraceItem[]`：Trace focus 的精确 Durable Facts；默认空数组；不受列表分页影响。
- `focused_audit: AuditLogItem | null`：Audit focus 的精确 Durable Fact；默认 `null`；不受列表分页影响。

后端字段事实保持：`WorkflowTraceEvent` 包含 `node_id`、`actor_id`、`data`、`error_code`、`error_message`；`AuditLog` 包含 `workflow_execution_id`、`operator_action_id`、`trace_id`、`request_id`、`metadata` 等字段。前端类型保持这些可空字段与后端模型一致。

## Contract 审查结论

2026-09-02 审查 `backend/app/services/runtime_operations/audit_trace_correlation.py` 与 `/api/v1/runtime/correlations/{executions,traces,audits,operator-actions}` 后确认：原实现的 Trace / Audit focus 仅通过 `by_trace` / `by_audit` 解析 Execution，再调用 `by_execution` 的分页列表；因此无法保证目标 Durable Fact 位于当前页。

根因不是前端定位逻辑，而是后端 response 缺少 focused-record Contract。此次采用最小后端修复：保留现有分页语义，仅增加精确 focused fact 查询结果，不改变分页总数、不扩大默认 page size、不改变 tenant scope、不通过时间或排序推导关系。

Trace 使用 `focused_traces` 而不是单一 `focused_trace`，因为同一 `trace_id` 在 `WorkflowTraceEvent` 中可能对应多个事件；返回全部精确匹配事实可以避免后端再次引入“第一条”猜测。Audit 使用唯一 `audit_id`，因此返回单一 `focused_audit`。

## Regression Test

Backend：

- `test_trace_focus_is_returned_outside_the_paginated_page`：验证 Trace focus 即使 `traces.items` 当前页为空，`focused_traces` 仍返回目标 Durable Facts。
- `test_audit_focus_is_returned_outside_the_paginated_page`：验证 Audit focus 即使 `audits.items` 当前页为空，`focused_audit` 仍返回目标 Durable Fact。

Frontend：

`WorkflowLifecycle.test.ts` 覆盖：

- `execution_id + trace_id` 深链恢复；
- `execution_id + audit_id` 深链恢复；
- Trace 上下文继续返回 Runtime 时保持真实 Execution / Trace ID；
- Audit 上下文继续返回 Runtime 时保持真实 Execution / Audit ID；
- 清除上下文不改变当前 Execution；
- 切换 Execution 后不会携带旧 Trace/Audit ID。

`RuntimeCorrelations.test.ts` 覆盖：

- Trace / Audit focus → WorkflowLifecycle 反向定位；
- 具体 Trace Durable Fact 字段定位；
- 具体 Audit Durable Fact 字段定位；
- 从具体 Trace 返回 WorkflowLifecycle 使用该行真实 Trace ID；
- 从具体 Audit 返回 WorkflowLifecycle 使用该行真实 Audit ID；
- Audit 自带真实 Trace ID 时继续进入 Trace focus；
- Audit `workflow_execution_id` 为空时回退到已确认的 Execution correlation。

## 本地验证

Frontend：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts
npm run build
```

Backend：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
pytest -q tests/unit/test_runtime_correlation_focused_facts.py
```

主线完成后再执行完整门禁：

```powershell
npm run test:unit
npm run test:gate
```

本轮采用：**Contract 审查 → 最小后端 focused-record Contract → targeted regression → 前端类型对齐 → 文档 → 原子提交**。

## 问题记录：Audit Execution ID 可空导致构建类型错误

2026-09-02 本地 targeted test 已通过 28/28，但 `npm run build` 在 `RuntimeCorrelations.vue` 报告 `string | null` 无法赋值给 `Record<string, string>`。

根因：后端 `AuditLog.workflow_execution_id` 是可空字段。前端此前在 Audit Durable Fact 反向定位 WorkflowLifecycle 时直接将该字段作为 `execution_id`，虽然运行时存在 Execution correlation 时可以回退，但 TypeScript 无法证明该值非空。

修复：保留后端可空 Contract，不通过类型断言掩盖问题；当选中 Audit Durable Fact 时优先使用其 `workflow_execution_id`，为空时回退到当前 correlation response 已确认的 `execution.id`。Trace Durable Fact 的 `execution_id` 仍保持必填事实来源。

因此 URL 生成仍满足：`execution_id` 必须是后端已确认的真实 Execution ID，禁止生成空字符串或通过启发式推导。

## 下一步

继续推进 RuntimeCorrelations 前端具体事实定位：消费后端 `focused_traces` / `focused_audit`，使 Trace/Audit 深链目标即使位于分页外也能直接展示，并补充对应 frontend regression test。仍禁止扩大分页和关系推导。
