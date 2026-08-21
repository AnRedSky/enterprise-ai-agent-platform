# 系统架构

## 1. 建设目标

建设企业级 AI Agent 平台，形成从需求分析、架构设计、核心研发、测试验证、部署上线到持续运营优化的工程体系。

核心目标：高可用、高并发、可维护、可扩展、多 Agent 协作、企业级安全、可观测和可治理。

## 2. 当前实现架构

```text
User / Enterprise App
        ↓
FastAPI API
        ↓
Auth / RBAC
        ↓
Agent Service
        ↓
Agent Runtime
 ├── Context / Session / Message
 ├── Model Gateway
 │    ├── Mock Provider
 │    └── OpenAI-compatible Provider
 ├── Tool Registry / Tool Runtime
 ├── Memory
 └── Observability
        ↓
Repository
        ↓
PostgreSQL / Redis
```

系统长期目标仍采用“接入层 → API/网关层 → Agent 编排层 → 能力层 → 数据层 → 基础设施层 → 运维治理层”的分层思想；实际实现以当前 FastAPI + Vue + PostgreSQL + Redis 单体边界为准。

## 3. 核心领域

| 领域 | 核心职责 |
|---|---|
| Identity | 用户、组织、角色、权限 |
| Agent | Agent 定义、配置、版本 |
| Runtime | Agent 执行生命周期 |
| Model | LLM、Embedding、Provider Contract |
| Tool | 工具注册、权限、执行 |
| Knowledge | 文档、知识库、RAG |
| Memory | Session / 长期记忆 |
| Session | 会话和上下文 |
| Workflow | 流程定义、版本、Execution、Trigger |
| Observability | Execution、Event、Trace、Token、Error、Audit |
| Governance | 生命周期、版本、发布、租户和审计 |

## 4. Agent Runtime

```text
Input
 ↓
Authentication
 ↓
Authorization
 ↓
Session Load
 ↓
Context Assembly
 ↓
Agent Router / Planner
 ↓
Model / Tool / Knowledge
 ↓
Result Validation
 ↓
Memory Update
 ↓
Output Guard
 ↓
Response
```

每次执行应具备可追踪标识：`request_id`、`trace_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`execution_id`。

生产环境禁止直接修改 Running Agent；修改应创建新版本并经过测试、评测和发布治理。

## 5. Model Gateway

Runtime 不直接依赖具体模型厂商。Provider 统一实现完成/流式调用 Contract，Model Gateway 统一处理：

- API Key
- 模型路由
- 超时 / 重试
- Token Usage
- 成本统计
- 限流 / 熔断 / Fallback
- 模型版本

Provider 类型与公共 Contract 保持单向依赖，避免 Gateway 与具体 Provider 循环依赖。

## 6. Tool Runtime

Tool 执行边界：

```text
Registry
  ↓
Agent Permission
  ↓
Input Schema
  ↓
Timeout / Limit / URL Safety
  ↓
Execute
  ↓
Audit
```

禁止任意 Python / Shell / 系统命令执行。HTTP Tool 必须执行协议、DNS 解析后的网络地址、超时和响应大小等安全检查。

## 7. Knowledge / RAG

```text
Document
 ↓
Parser / Cleaner
 ↓
Chunker
 ↓
Embedding
 ↓
Vector / Retrieval
 ↓
Reranker
 ↓
Context Builder
 ↓
LLM
```

知识数据必须保持文档版本、Chunk 版本、Embedding 版本、权限过滤、引用溯源和检索评测边界。

## 8. Memory

Memory 位于 Runtime 与持久化层之间。基础能力采用 PostgreSQL MemoryRecord 与 MemoryService，Session 级查询优先当前 Session，同时允许读取用户/Agent 级长期记忆；必须受用户、Agent、Session 可见性和数量限制约束。

## 9. Workflow / Trigger

Workflow 采用：

```text
Workflow Definition
 ↓
Workflow Version
 ↓
Publish Governance
 ↓
Trigger
 ↓
Execution State Machine
 ↓
Runtime
 ↓
Audit / Trace
```

Scheduled Trigger 与 Webhook Trigger 共用 Trigger Domain / Execution Contract，但入口机制保持独立。Webhook 不执行任意代码，也不直接引入 MQ/Event Bus。

## 10. 数据与版本

Agent 与 AgentVersion 分离；Workflow 与 Workflow Version 分离。执行记录必须绑定实际版本，避免配置漂移导致历史执行不可追溯。

## 11. 前端

Vue 负责管理端交互和调试体验，不承担 Agent 核心业务规则。所有业务操作通过版本化 API 完成；前端 API Types 必须以 Backend Contract 为准。