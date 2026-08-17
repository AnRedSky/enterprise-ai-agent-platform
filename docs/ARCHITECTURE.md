# 系统架构

## 目标

建设企业级 AI Agent 平台，核心执行链路以 Agent Runtime 为中心，并通过 Model Gateway、Tool Runtime、Memory、Observability 形成可治理的执行闭环。

## 核心链路

```text
User
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
 └── Observability
 ↓
PostgreSQL / Redis
```

## Model Gateway

Runtime 不直接依赖具体模型厂商。Provider 实现统一 `complete` 和 `stream` 协议；模型调用结果统一记录 `model` 与可选 Token Usage。

## Tool 安全边界

Tool 执行必须经过：

```text
Registry → Agent Permission → Input Schema → Timeout / Limit → Execute → Audit
```

禁止将任意代码执行能力暴露给 Agent。

## 数据与版本

Agent 与 AgentVersion 分离。执行记录必须绑定具体 Agent Version，避免配置漂移导致历史执行不可追溯。

## 前端

Vue 负责管理端交互和调试体验；不直接承担 Agent 核心业务规则。所有业务操作通过版本化 API 完成。
