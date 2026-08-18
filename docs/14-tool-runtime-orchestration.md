# 14 - Tool Runtime 完整编排与审计闭环

## 1. 上一阶段

完成 Observability 第一版：Execution、ExecutionEvent、Model Call span、request/trace/execution 关联、Token Usage、latency、状态与错误记录。

## 2. 本阶段目标

将已有 Tool Registry、AgentTool、Schema Validator、HTTP Executor 和 Observability 串成完整安全执行链。

## 3. 开发原则

- 文档先行后编码。
- Tool 必须绑定 Agent 才允许执行。
- Tool 必须启用。
- 执行前必须完成参数 Schema 校验。
- HTTP Executor 保持 SSRF、timeout、response size 安全边界。
- 禁止任意 Python / Shell 执行。
- 单次 Execution 限制 Tool 调用次数。
- Tool 执行必须写 AuditLog。
- Tool span 必须关联 Execution。
- 不记录 API Key、Authorization、Cookie 和完整敏感参数。

## 4. 执行链

```text
Agent Runtime
    ↓
Tool Runtime Service
    ↓
AgentTool Binding
    ↓
Enabled Check
    ↓
Permission Check
    ↓
Schema Validation
    ↓
Execution Limit
    ↓
Tool Executor
    ↓
AuditLog + Tool Span
    ↓
Tool Result
```

## 5. 交付范围

### P0-1 Registry
验证 Tool 存在、AgentTool 绑定关系和 Tool enabled 状态。

### P0-2 Permission
执行前校验调用主体与 Agent/Tool 的授权边界，拒绝未授权调用。

### P0-3 Schema
所有参数在进入 Executor 前通过对象 Schema 校验。

### P0-4 Executor
复用安全 HTTP Executor；禁止绕过 Runtime 直接调用外部 HTTP。

### P0-5 Execution Limit
每个 Agent Execution 设置 Tool 调用上限，防止循环调用和资源耗尽。

### P0-6 AuditLog
记录 actor、agent、tool、action、request_id、trace_id、execution_id 和时间；敏感字段脱敏或不落库。

### P0-7 Observability
创建 Tool Execution Event / span，记录 latency、status、error，并关联 execution_id。

## 6. 测试验收

必须覆盖：

- Tool 不存在
- Tool 未绑定 Agent
- Tool disabled
- Permission denied
- Schema invalid
- SSRF blocked
- timeout
- response too large
- execution limit
- AuditLog
- Tool span
- success / failure

## 7. 下一阶段

完成后提交 `docs/15-tool-runtime-completion.md`，并在同一次完成提交中写明下一阶段 `16` 的详细规划。下一阶段预定进入 Memory/Tool 与 Observability 的统一查询与管理能力。
