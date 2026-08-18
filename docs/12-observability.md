# 12 - Observability 设计与实施计划

## 1. 开发基线

本阶段基于 `main` 最新代码开发。上一阶段已完成 Memory Governance 第一版；本阶段正式进入 Observability。

## 2. 文档先行规则

本文件必须与本阶段完成代码一起存在于同一个可追踪的 `main` 提交历史中。开发顺序固定为：

1. 编写/评审本阶段规划文档
2. 实现代码
3. 增加测试
4. 提交完成记录
5. 在完成记录中明确下一阶段详细计划

## 3. 目标

建立统一的 Agent Execution 可观测性基础能力，为模型调用、Tool 调用、Memory 访问和 API 请求提供关联 ID、状态、耗时、Token 使用量及错误信息。

## 4. 核心标识

统一支持：

- `request_id`
- `trace_id`
- `execution_id`
- `session_id`
- `agent_id`
- `agent_version`
- `model_id`
- `tool_id`

其中 `trace_id` 用于一次请求链路关联，`execution_id` 用于一次 Agent Runtime 执行关联。

## 5. Execution 生命周期

```text
started
  ↓
running
  ↓
completed / failed
```

每次执行至少记录：开始时间、结束时间、状态；失败时记录错误类型和安全的错误消息。

## 6. Model / Tool / Memory Span

第一版采用轻量数据库事件模型，不引入 OpenTelemetry Collector 等额外基础设施。

建议事件结构：

```text
Execution
 ├── Model Call
 ├── Tool Call
 └── Memory Access
```

事件字段包括：

- execution_id
- trace_id
- span_type
- status
- started_at
- ended_at
- duration_ms
- model_id / tool_id（适用时）
- token usage（模型调用适用时）
- error_code / error_message（失败时）

## 7. 数据安全

禁止记录：

- API Key
- Authorization Header
- 密码
- Cookie
- 完整敏感请求头

用户消息和模型完整响应默认不写入 Observability 表；如未来需要 Debug Payload，必须单独设计脱敏与权限策略。

## 8. 实施顺序

### P0

1. `Execution` / `ExecutionEvent` 数据模型
2. Alembic Migration
3. Observability Service
4. Runtime execution 生命周期埋点
5. Model Call usage / latency 记录
6. 错误记录

### P1

7. Tool Call span
8. Memory Access span
9. request_id / trace_id 中间件
10. API 查询接口

### P2

11. Vue Observability 页面
12. OpenTelemetry / Metrics 后端适配

## 9. 验收标准

- 正常 Agent execution 有 started/completed 记录
- Runtime 异常产生 failed 记录
- Model 调用记录 latency 和 token usage
- 同一次请求可以通过 trace_id / execution_id 关联事件
- 敏感信息不进入日志/数据库
- Migration 可升级且不修改历史 migration
- 单元测试与集成测试覆盖核心生命周期

## 10. 本阶段交付物

```text
backend/app/models/execution.py
backend/app/services/observability_service.py
backend/alembic/versions/0004_observability.py
backend/tests/test_observability.py
docs/13-observability-completion.md
```

## 11. 下一阶段预告

完成本阶段后进入 Tool Runtime 完整编排与审计闭环：Registry → Permission → Schema → Executor → AuditLog，并创建下一编号开发规划文档。
