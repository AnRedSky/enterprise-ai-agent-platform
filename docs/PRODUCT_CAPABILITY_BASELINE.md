# 企业级 AI Agent 平台产品能力基线

> 基线：远端 `main` 最新提交 `718aee7016f814816a4168d3600c389c00f99561`
> 评估日期：2026-08-22
> 文档性质：产品能力与工程实现基线，不代表下一 Phase 已经立项。

## 1. 产品定位

Enterprise AI Agent Platform 是面向企业应用的 AI Agent 平台。当前技术实现采用 FastAPI + Vue 3 + PostgreSQL + Redis 单体边界，通过版本化 API 提供 Agent、Runtime、Model、Tool、Knowledge、Memory、Workflow、Trigger、Observability 与 Governance 能力。

产品长期建设目标包括高可用、高并发、可维护、可扩展、多 Agent 协作、企业级安全、可观测和可治理；当前实际实现必须以仓库代码、当前 Phase 文档及 Acceptance 证据为准。

## 2. 当前产品架构

```text
User / Enterprise App
        ↓
FastAPI API
        ↓
Auth / RBAC / Tenant Governance
        ↓
Agent / Workflow Services
        ↓
Agent Runtime / Workflow Runtime
 ├── Context / Session / Message
 ├── Model Gateway
 │    ├── Mock Provider
 │    └── OpenAI-compatible Provider
 ├── Tool Registry / Tool Runtime
 ├── Knowledge / RAG
 ├── Memory
 ├── Trigger / Scheduler / Webhook
 └── Observability / Audit / Trace
        ↓
Repository
        ↓
PostgreSQL / Redis

Vue 3 Management / Debug UI
        ↓
Versioned Backend API Contract
```

当前系统分层原则为 API → Service → Runtime → Gateway / Tool / Memory / Knowledge → Repository → PostgreSQL / Redis。前端只负责管理端交互和调试体验，不承载核心领域规则。

## 3. 产品能力全景

| 能力域 | 产品能力 | 当前工程状态 | 当前验收结论 | 主要边界 |
|---|---|---|---|---|
| Identity / Auth | 用户认证、角色、权限、Tenant scope | 已实现 | 已纳入各阶段 Gate | 当前为平台级 RBAC，不等同完整组织 IAM 产品 |
| Agent | Agent 定义、配置、版本、Owner/RBAC | 已实现 | Phase 1.2/1.3 基础能力已完成 | 当前未形成完整企业 Agent Marketplace / 发布生态 |
| Agent Runtime | Session、Context、Message、执行生命周期 | 已实现 | Phase 1.3 + Phase 1.9 Reliability Gate 通过 | 仍保持单体 Runtime 边界 |
| Model Gateway | Provider Contract、普通/流式调用、错误/超时、Usage | 已实现 | Phase 1.3 当前范围完成 | Provider 路由、Fallback、成本治理等长期目标需按新需求继续定义 |
| Tool Runtime | Registry、AgentTool、Schema、权限、HTTP Executor、安全限制、Audit | 已实现 | 历史能力已归并到 Phase 1.3，当前状态以最新 Gate 为准 | 禁止任意 Python/Shell/系统命令；当前不是通用代码执行平台 |
| Memory | PostgreSQL MemoryRecord、put/list/search、Session/User/Agent visibility | 已实现 | Phase 1.3 当前范围完成 | 不包含向量记忆、自动摘要、LLM 自动长期记忆等历史 Out of Scope |
| Observability | Execution/Event/Trace/Usage/Error/Audit 关联、查询与管理 UI | 已实现 | Phase 1.3 + 1.9 验收闭环 | 当前不等同完整分布式 Observability 平台 |
| Knowledge | Knowledge Base、Document、Version、Chunk、Ingestion | 已实现 | Phase 1.4 当前范围完成 | 生产语义质量仍需以真实 Provider 结果验证 |
| Retrieval | Lexical、Vector、Hybrid、Evaluation、Debug、Citation | 已实现 | Phase 1.4 当前范围完成 | Mock Embedding 只验证工程链路，不代表真实语义质量 |
| Workflow | Definition、Version、Publish、Execution State Machine、Runtime | 已实现 | Phase 1.5 正式关闭 | 当前不是复杂 DAG / Temporal / Saga 编排平台 |
| Workflow Governance | Tenant、Owner/Admin、Audit、Trace、Retry、Timeout、Idempotency | 已实现 | Phase 1.5/1.9 通过 | 已验证边界不得无原因重复修改 |
| Circuit Breaker | CLOSED/OPEN/HALF_OPEN、Policy persistence、Drift、Probe quota | 已实现 | Phase 1.5-G + 1.9 Real API 通过 | 后续仅因新需求或 Gate 回归继续扩展 |
| Manual Trigger | Trigger CRUD、Enable/Disable、Invoke | 已实现 | Phase 1.6 关闭 | 入口复用 Workflow Execution Governance |
| Scheduled Trigger | timezone + interval_seconds、Scheduler、slot idempotency、recovery | 已实现 | Phase 1.7 正式关闭 | 当前没有 next_run_at、scheduler lease、misfire policy、独立 scheduler state |
| Webhook Trigger | Secret、event identity、durable idempotency、lifecycle、Execution | 已实现 | Phase 1.8 正式关闭 + Browser E2E | 当前没有通用 Event Bus / MQ / Kafka |
| Frontend Governance | Agent/Workflow/Trigger/Knowledge/Runtime/Audit 管理与调试 | 已实现 | Frontend Regression / Build / Browser Gate 已通过 | UI 不实现后端治理规则 |
| Browser E2E | Browser → Vue → HTTP → Backend → Runtime | 已实现 | 最新 Phase 1.9 Browser Gate 通过 | E2E 是独立 Gate，不替代 Backend/Frontend Gate |

## 4. 核心业务闭环

### 4.1 Agent Runtime

```text
Authentication
 → Authorization
 → Session Load
 → Context Assembly
 → Agent Runtime
 → Model / Tool / Knowledge
 → Result Validation
 → Memory Update
 → Output
 → Observability / Audit
```

每次执行应保持 request、trace、session、agent、version、model、execution 等标识可追踪。

### 4.2 Knowledge / RAG

```text
Document
 → Parser / Cleaner
 → Deterministic Chunk
 → Embedding Provider
 → Vector / Lexical / Hybrid Retrieval
 → Context Builder
 → Runtime
 → Citation / Debug / Trace
```

线上 Retrieval 的业务数据来源必须是数据库；评测 JSON 仅为评测产物，不得作为线上业务数据源。

### 4.3 Workflow

```text
Workflow Definition
 → Version
 → Publish
 → Trigger
 → Execution State Machine
 → Runtime
 → Audit / Trace
```

Workflow Execution 绑定创建时的 Published Version，并受到 Tenant / RBAC / Idempotency / Retry / Timeout / Circuit Breaker 约束。

### 4.4 Trigger

```text
Manual Trigger
      │
Scheduled Trigger ──┐
      │              ├→ Trigger Governance → Workflow Execution
Webhook Trigger ────┘                         ↓
                                        Audit / Trace
```

Scheduled 与 Webhook 共用 Trigger / Execution 治理边界，但调度和外部事件入口保持独立。

## 5. 安全与治理基线

- Tenant scope 必须由认证上下文和后端 Service 决定，客户端不得自行提交 Tenant。
- Owner / Admin 权限必须由 Backend Contract 执行，前端只展示结果。
- Tool Runtime 禁止任意 Python / Shell / 系统命令执行。
- HTTP Tool 必须执行协议、DNS 解析后的 IP、超时、响应大小等安全检查。
- Webhook Secret 只写入，不从 response 返回，持久化只保存 hash。
- 真实 Provider endpoint、API key、model 等敏感配置只能存在未提交的 `backend/.env`。
- 已验证的 Runtime Reliability 边界不能无原因回退。

## 6. 当前可靠性基线

最新项目状态记录的本地证据：

- Backend：264 passed，23 deselected。
- Migration：`0022_workflow_trigger` 为 head，`upgrade head/current/heads` 已实际验证。
- Real API：23 passed。
- Frontend：13 test files / 52 tests passed，production build passed。
- Browser：Desktop Chrome 3 passed。

上述结果是当前 Phase 1.9 Acceptance 记录的实际本地证据；新任务不得将其重新解释为本轮重新执行的结果。

## 7. 当前明确未覆盖的产品能力

以下内容在当前 Phase 文档中属于明确 Out of Scope 或尚未形成新 Phase，不应在没有产品需求/架构决策的情况下直接实现：

1. MQ / Kafka / 通用 Event Bus。
2. Temporal / Airflow 等分布式 Workflow Engine。
3. 复杂 DAG、Saga、复杂 Policy DSL。
4. Multi-Agent orchestration / 多 Agent 协作产品能力。
5. 可视化拖拽 Workflow Designer。
6. 任意代码执行平台。
7. 完整企业 IAM / 组织管理产品。
8. 完整分布式 Scheduler（lease、misfire、独立 scheduler state 等）。
9. 真实 Embedding Provider 的语义质量结论；当前只能通过实际 Provider 验证确认。

这些条目是“产品边界 / 待决策能力”，不是当前自动生成的开发任务。

## 8. 下一阶段决策原则

Phase 1.9 已正式关闭。当前仓库没有正式定义新的 Phase 2.x，因此下一阶段必须先完成需求与架构基线决策，再创建新的 `docs/02-phases/PHASE_x_y.md` 与 Acceptance 文档。

下一阶段候选项应按以下顺序评估：

1. 企业真实使用场景与产品价值；
2. 当前 Phase 明确未覆盖的能力缺口；
3. 当前代码中已经出现但尚未形成完整产品 Contract 的能力；
4. 真实 Provider / 数据质量 / 运维约束；
5. 对现有 Runtime Reliability 边界的影响；
6. Backend Contract、Migration、Frontend、Real API、Browser E2E 的完整验收成本。

不得因为历史文档存在旧的“Phase 14～24”编号，就重新创建这些旧阶段；当前项目只使用 `PHASE_1_x` 及经正式决策后的新阶段编号。
