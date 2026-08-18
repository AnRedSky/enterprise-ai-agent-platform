# 22 - Runtime Management API & Vue Integration 规划

## 1. 来源

Phase 20 完成 Runtime Observability & Governance Query，形成数据库内的 Execution、Event、Audit 查询能力。本阶段进入管理端 API 与 Vue 只读集成。

## 2. 目标

为管理端提供统一、只读、受 RBAC 保护的 Runtime 管理视图：

- Execution 列表与详情
- Execution timeline
- Tool / Model spans
- Audit events
- trace / request / session 查询

## 3. 开发原则

- 文档先行后编码。
- 管理端 API 不绕过现有 Service / RBAC。
- 默认最小字段返回。
- 不返回 secret、Authorization、Cookie、完整敏感参数和内部堆栈。
- 所有列表分页，限制最大 page size。
- Vue 只调用后端管理 API，不直接访问数据库。
- 不改变 SSE Runtime 主链路。

## 4. Backend API

实现并稳定：

```text
GET /api/v1/executions
GET /api/v1/executions/{execution_id}
GET /api/v1/executions/{execution_id}/events
GET /api/v1/audit-logs
```

统一 query：

- page
- page_size
- status
- agent_id
- tool_id
- model_id
- trace_id
- request_id
- session_id
- started_from
- started_to

最大 page_size 必须由服务端强制限制。

## 5. Response Contract

统一：

```text
items
page
page_size
total
```

Execution DTO：

```text
execution_id
request_id
trace_id
session_id
agent_id
agent_version
model_id
status
started_at
ended_at
duration_ms
error_code
```

Event DTO：

```text
event_id
execution_id
trace_id
span_type
status
started_at
ended_at
duration_ms
model_id
tool_id
token_usage
error_code
```

## 6. RBAC

Owner 和 Admin 可以查看授权范围内的数据；无关用户必须返回 403/404，不泄露资源存在性。

## 7. Vue 管理端

新增 Runtime 页面：

```text
Runtime
 ├── Execution List
 ├── Execution Detail
 │    └── Timeline
 │         ├── Model Span
 │         └── Tool Span
 └── Audit Log
```

支持分页、过滤、详情查看和错误状态展示。

## 8. 测试

Backend：

- API contract
- RBAC
- pagination
- filters
- redaction

Frontend：

- API client
- list rendering
- filters
- pagination
- detail timeline
- permission denied
- empty / error states

## 9. 交付规则

Phase 22 完成时必须同时提交：

- Backend API
- Vue 页面及 API client
- 测试
- `docs/23-runtime-management-completion.md`
- `docs/24-下一阶段详细规划.md`

即：

```text
22 文档先行
 ↓
22 开发
 ↓
23 完成记录 + 24 下一阶段规划
```

## 10. 非目标

本阶段不引入 OpenTelemetry、外部 APM、消息队列或缓存；不重构现有 SSE Runtime。
