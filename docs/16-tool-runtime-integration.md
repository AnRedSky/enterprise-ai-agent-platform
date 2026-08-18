# 16 - Tool Runtime Integration & Audit

## 1. 上一阶段

Phase 15 完成 ToolRuntimeService 编排骨架：Tool/AgentTool 校验、Permission 注入、Schema 校验、调用次数限制、安全 HTTP Executor、Audit/Observability 注入点。

## 2. 本阶段目标

将 Tool Runtime 从编排骨架接入真实数据库、RBAC、AuditLog 和 Observability，形成可验收的端到端治理闭环。

## 3. 开发顺序

文档完成并提交后才开始编码，顺序固定：

1. Repository Adapter
2. RBAC Adapter
3. AuditLog Persistence
4. Tool Observability Persistence
5. HTTP Security 补强
6. E2E 测试
7. Tool API 设计与实现（仅在治理链稳定后）

## 4. Repository Adapter

复用现有 SQLAlchemy Session/Repository 模式，ToolRuntimeService 不直接操作 ORM。

必须支持：

- Tool 查询
- AgentTool 查询
- Tool enabled 状态
- AgentTool enabled 状态
- 按 agent_id + tool_id 精确绑定查询

## 5. RBAC Adapter

Runtime 必须通过统一权限服务检查 actor 对 Agent/Tool 的调用权限。

禁止 API 层单独判断后绕过 Runtime。

权限失败统一返回 `PERMISSION_DENIED`。

## 6. AuditLog Persistence

Tool 执行成功和失败都写入 AuditLog。

允许字段：

- actor_id
- agent_id
- tool_id
- execution_id
- trace_id
- request_id
- action
- status
- created_at

禁止持久化：

- API Key
- Authorization
- Cookie
- 完整敏感 headers
- 未脱敏 secret
- 不必要的完整 Tool 参数

## 7. Observability Persistence

Tool span 必须关联 Execution：

```text
Execution
  └── Tool Event
       ├── tool_id
       ├── execution_id
       ├── trace_id
       ├── status
       ├── latency_ms
       └── error
```

## 8. HTTP Security

补充测试并修复：

- localhost
- loopback
- private IP
- link-local
- metadata endpoint
- DNS resolution
- redirect 到受限地址
- timeout
- response size limit

redirect 不得绕过目标地址安全检查。

## 9. E2E 验收

使用真实数据库验证：

```text
Agent
 ↓
AgentTool
 ↓
Permission
 ↓
Schema
 ↓
Execution Limit
 ↓
HTTP Executor
 ↓
AuditLog
 ↓
Tool Observability
```

覆盖 success / failure / denied / disabled / invalid schema / limit exceeded / SSRF。

## 10. 交付规则

本阶段完成时必须在同一阶段交付中提交：

- 全部代码
- Migration（如需要）
- 测试
- `docs/17-tool-runtime-integration-completion.md`
- 下一阶段 `18` 的详细规划

即：**16 文档先行；完成 16 时必须同时提交 17 + 18。**
