# 13 - Observability 完成记录与下一阶段计划

## 1. 上一阶段

完成 Memory Governance 第一阶段，并建立了“规划文档先行”的开发流程。

## 2. 本阶段完成

本阶段在 `main` 上完成 Observability 第一版：

- `Execution` 数据模型
- `ExecutionEvent` 数据模型
- `0004_observability` Alembic Migration
- `ObservabilityService`
- Agent Chat Runtime execution 生命周期埋点
- Model Call span
- request_id / trace_id / execution_id 关联
- Model token usage 记录
- latency / status / error 记录
- 失败时统一错误信息，不记录敏感 payload
- Observability 基础单元测试

## 3. Runtime 链路

```text
Chat Request
  ↓
request_id + trace_id
  ↓
Execution(running)
  ↓
Model Call Event
  ↓
Execution(completed / failed)
  ↓
SSE done
```

SSE `done` 事件现在返回真实 `execution_id` 与记录的 `latency_ms`。

## 4. 数据安全

当前 Observability 不记录 API Key、Authorization Header、Cookie、完整用户消息或完整模型响应；模型失败只保存安全的错误类型和固定错误消息。

## 5. 测试与限制

已增加基础 Service 测试。由于 CI 自动执行目前处于临时暂停状态，本次不宣称远端 CI 已通过；后续恢复 CI 后必须重新验证 Migration、API、Runtime 集成测试。

当前尚未完成：

- Tool Call span
- Memory Access span
- request_id / trace_id 全局 HTTP Middleware
- Observability 查询 API
- Vue Observability 页面
- OpenTelemetry / Metrics 适配

## 6. 下一阶段详细计划：Tool Runtime 完整编排与审计闭环

下一阶段编号从 `14` 开始，必须先提交 `docs/14-tool-runtime-orchestration.md`，再进行编码。

### P0-1 Registry

```text
Agent
 ↓
AgentTool
 ↓
Tool
```

验证 Tool 是否存在、是否启用、是否已经绑定当前 Agent。

### P0-2 Permission

在执行前校验当前用户/Agent 对 Tool 的访问权限。管理员能力与普通用户能力必须明确隔离。

### P0-3 Schema

调用参数进入 Executor 前必须执行 Schema 校验，拒绝未知字段和错误类型。

### P0-4 Executor

HTTP Executor 继续保持安全边界：

- HTTP/HTTPS only
- SSRF 防护
- timeout
- response size limit
- redirect 安全策略

禁止任意 Python / Shell 执行。

### P0-5 Execution Limit

增加单次 Agent Execution 的 Tool 调用次数限制，防止循环调用和资源耗尽。

### P0-6 AuditLog

Tool 调用必须写入 AuditLog，至少记录：

- actor_id
- agent_id
- tool_id
- action
- request_id
- trace_id
- execution_id（若 AuditLog schema 扩展）
- created_at

不得写入密钥、Authorization Header 或完整敏感参数。

### P0-7 Observability Integration

Tool Runtime 必须创建：

```text
Execution
  └── tool span
```

将 Tool latency、status、error 与 execution 关联。

### P0-8 Test

覆盖：

- Tool 未绑定
- Tool disabled
- Permission denied
- Schema invalid
- SSRF blocked
- timeout
- response too large
- execution limit
- AuditLog
- tool span
- success / failure

### P0-9 完成记录

完成后必须提交：

```text
docs/15-tool-runtime-completion.md
```

其中必须同时记录本阶段完成情况和下一阶段 `16` 的详细规划。

## 7. 本阶段提交要求

当前代码、测试、Migration 和本完成记录必须全部位于 `main` 的最新开发历史中。不得提交 ZIP、日志、`.env`、缓存、构建产物或其他非项目文件。
