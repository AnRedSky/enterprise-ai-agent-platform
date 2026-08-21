# Phase 1.3 — Model Gateway / Tool Runtime / Memory / Observability

## 1. 阶段目标

在 Phase 1.2 基础平台上形成 Agent Runtime 的核心执行闭环，并建立 Model Gateway、Tool Runtime、Memory、Observability 与基础管理端能力。

## 2. Model Gateway

统一 Provider Contract、ModelResult、ModelUsage、普通/流式调用和错误/超时边界。Runtime 不直接依赖具体模型厂商 SDK 或 HTTP 实现。

```text
Agent Runtime
      ↓
Model Gateway
      ↓
Provider Contract
   ├── Mock
   └── OpenAI-compatible
```

## 3. Tool Runtime

第一版要求：

- Tool Registry / AgentTool 权限关联
- JSON Schema 参数校验
- HTTP Tool Executor
- Timeout / response size limit
- SSRF / restricted IP 防护
- Tool invocation limit
- AuditLog
- Runtime 与 Executor 解耦

禁止任意 Python、Shell、系统命令执行；HTTP Tool 必须进行协议、DNS 解析后 IP、超时和响应体大小检查。

## 4. Memory

采用 PostgreSQL 基础 MemoryRecord / MemoryService。支持 `put()`、`list_for_context()`、`search()`；Session 级查询优先当前 Session，并受 user / agent / session visibility 与 context limit 约束。

本阶段不引入向量数据库、embedding、自动摘要、LLM 自动写长期记忆或跨租户共享记忆。

## 5. Observability

Execution、Event、Trace、Token Usage、Error、Audit 必须可关联到 request / trace / session / agent / version / model / execution 标识。

## 6. 前端

Vue 管理端通过版本化 API 访问业务能力，不在前端实现核心领域规则。测试与业务源码分离。

## 7. 任务拆解

```text
1.3-A Model Gateway
1.3-B Tool Runtime
1.3-C Tool Runtime Security / Validation
1.3-D Memory
1.3-E Memory Runtime Integration
1.3-F Observability
1.3-G Runtime / Management Frontend
```

历史根级 `03/04/05/06` 文档已按本 Phase 合并；其中实际验证结果进入 `03-acceptance/PHASE_1_3_ACCEPTANCE.md`。