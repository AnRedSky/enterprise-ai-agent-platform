# 20 - Runtime Observability & Governance Query 规划

## 1. 来源

Phase 18 已完成 Tool Runtime 的 E2E、安全和审计闭环。本阶段从“能执行”进入“可查询、可追踪、可治理”。

## 2. 目标

提供统一 Runtime Observability 查询模型，让 Agent、Model、Tool、Memory 的 Execution 数据可以按 request_id、trace_id、execution_id、session_id、agent_id 查询，并为管理端提供稳定的数据接口。

## 3. 开发原则

- 文档先行后编码。
- 查询接口不得绕过现有权限边界。
- 默认只返回必要的非敏感字段。
- AuditLog 与 ExecutionEvent 不暴露 secret、Authorization、Cookie 和完整敏感参数。
- 分页、排序和时间范围必须有上限。
- Runtime 写入链路与查询链路分离，避免查询影响执行。

## 4. 开发顺序

### P0-1 Query Repository

新增 Observability Query Repository：

- Execution detail
- Execution timeline
- Tool spans
- Model spans
- Audit events

支持：

- execution_id
- trace_id
- request_id
- session_id
- agent_id
- status
- time range

### P0-2 Permission

查询必须验证：

```text
actor
 ↓
agent ownership / admin
 ↓
execution visibility
```

禁止普通用户读取其他 Agent 的 Execution。

### P0-3 API

规划只读接口：

```text
GET /api/v1/executions/{execution_id}
GET /api/v1/executions/{execution_id}/events
GET /api/v1/executions
GET /api/v1/audit-logs
```

所有列表接口必须分页并限制最大 page size。

### P0-4 Response DTO

统一输出：

- execution_id
- request_id
- trace_id
- agent_id
- status
- duration_ms
- started_at
- ended_at
- events

错误消息必须避免暴露内部堆栈和外部服务敏感信息。

### P0-5 Filtering

支持：

- status
- agent_id
- tool_id
- model_id
- trace_id
- time range

禁止无限时间范围和无限分页。

### P0-6 Tests

覆盖：

- owner can query
- admin can query
- unrelated user denied
- pagination
- max page size
- filters
- execution timeline
- tool span
- model span
- audit redaction

## 5. 交付规则

完成 Phase 20 时必须同时提交：

- 代码
- 测试
- `docs/21-runtime-observability-governance-completion.md`
- 下一阶段 `22` 详细规划

即继续执行：

```text
20 文档先行
 ↓
20 开发
 ↓
21 完成记录 + 22 下一阶段规划
```

## 6. 非目标

本阶段不引入新的可观测性基础设施，不引入外部 APM；先完成数据库内 Runtime 查询和治理闭环，再根据后续需求评估 OpenTelemetry/外部 Trace 系统。
