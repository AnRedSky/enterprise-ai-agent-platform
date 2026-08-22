# 企业级 AI Agent Platform 产品能力基线

> 基线：远端 `main` 当前规划基线 `3d902ca2db35b8c62ce297e7e370924888219269`
> 评估日期：2026-08-22
> 文档性质：产品能力与工程实现基线；Phase 1.9 已关闭，Phase 2.1 已立项。

## 1. 产品定位

Enterprise AI Agent Platform 是面向企业应用的 AI Agent 平台。当前技术实现采用 FastAPI + Vue 3 + PostgreSQL + Redis 单体边界，通过版本化 API 提供 Agent、Runtime、Model、Tool、Knowledge、Memory、Workflow、Trigger、Observability 与 Governance 能力。

长期目标包括高可用、高并发、可维护、可扩展、多 Agent 协作、企业级安全、可观测和可治理；实际完成度必须以仓库代码、Phase 文档及 Acceptance 证据为准。

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

| 能力域 | 当前工程状态 | 当前验收结论 | 主要边界 / 下一动作 |
|---|---|---|---|
| Identity / Auth | 已实现 | Phase 1.x 已验收当前范围 | Phase 2.1 扩展 Organization / Membership；不等同完整 SSO/SCIM IAM |
| Agent | 已实现 | 当前范围已验收 | Marketplace / 发布生态为 Phase 2.8 候选 |
| Agent Runtime | 已实现 | Phase 1.9 Reliability Gate 已通过 | 保持可靠性基线 |
| Model Gateway | 已实现 | 当前范围已验收 | Provider 路由/Fallback/成本治理为 Phase 2.3 候选 |
| Tool Runtime | 已实现 | 当前范围已验收 | 禁止任意代码执行 |
| Memory | 已实现 | 当前范围已验收 | 向量记忆/自动摘要需独立需求 |
| Observability | 已实现 | 当前范围已验收 | 不等同完整分布式 Observability 平台 |
| Knowledge | 已实现 | Phase 1.4 当前范围完成 | 真实 Provider 语义质量进入 Phase 2.2 |
| Retrieval | 已实现工程链路 | Phase 1.4 当前范围完成 | 生产语义质量需真实 Provider + 数据集 + 指标 |
| Workflow | 已实现 | Phase 1.5 正式关闭 | 复杂 DAG/Saga/Designer 为 Phase 2.5 候选 |
| Workflow Governance | 已实现 | Phase 1.5/1.9 已验收 | Organization scope 进入 Phase 2.1 |
| Circuit Breaker | 已实现 | Phase 1.9 Real API 已验收 | 只因新需求或回归继续扩展 |
| Manual Trigger | 已实现 | Phase 1.6 已关闭 | 保持 |
| Scheduled Trigger | 已实现 | Phase 1.7/1.9 已验收 | Durable Scheduler 为 Phase 2.4 候选 |
| Webhook Trigger | 已实现 | Phase 1.8/1.9 Browser 已验收 | 通用 Event Infrastructure 为 Phase 2.6 候选 |
| Frontend Governance | 已实现 | Frontend Regression / Build / Browser Gate 已通过 | Phase 2.1 增加 Organization 管理 UI |
| Browser E2E | 已实现 | Phase 1.9 已验收 | 新功能必须新增独立 E2E |

## 4. 当前核心业务闭环

### Agent Runtime

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

### Knowledge / RAG

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

### Workflow / Trigger

```text
Workflow Definition
 → Version
 → Publish
 → Trigger
 → Execution State Machine
 → Runtime
 → Audit / Trace
```

Manual、Scheduled、Webhook 共用 Trigger / Execution 治理边界，但入口保持独立。

## 5. 企业产品化缺口与路线

按真实企业使用价值排序：

1. **Phase 2.1 — Organization & Access Governance（P0）**：解决组织、成员、角色和资源边界。
2. **Phase 2.2 — Retrieval Production Quality（P0）**：解决真实 Embedding Provider、质量数据集和可量化指标。
3. **Phase 2.3 — Model Provider Governance（P1）**：解决模型路由、Fallback、白名单和成本/用量治理。
4. **Phase 2.4 — Durable Scheduler（P1）**：解决 `next_run_at`、lease、misfire 和多实例恢复语义。
5. **Phase 2.5 — Advanced Workflow Orchestration（P1）**：解决复杂 DAG、并行/条件、补偿等真实流程需求。
6. **Phase 2.6 — Enterprise Event Infrastructure（P2）**：只有真实业务证明 Webhook 不足时再引入 MQ/Event Bus。
7. **Phase 2.7 — Multi-Agent Collaboration（P2）**：先定义业务协作场景、权限、状态和成本边界。
8. **Phase 2.8 — Agent Asset / Marketplace（P2）**：形成企业 Agent 资产复用、发布和治理。

完整路线见 `docs/PRODUCT_ROADMAP.md`。

## 6. 安全与治理基线

- Tenant / Organization scope 必须由认证上下文和后端 Service 决定，客户端不得自行决定授权范围。
- Owner / Admin 权限必须由 Backend Contract 执行，前端只展示结果。
- Tool Runtime 禁止任意 Python / Shell / 系统命令执行。
- HTTP Tool 必须执行协议、DNS 解析后的 IP、超时、响应大小等安全检查。
- Webhook Secret 只写入，不从 response 返回，持久化只保存 hash。
- 真实 Provider endpoint、API key、model 等敏感配置只能存在未提交的 `backend/.env`。
- 已验证的 Runtime Reliability 边界不能无原因回退。

## 7. 当前可靠性基线

Phase 1.9 已记录的本地证据：

- Backend：264 passed，23 deselected。
- Migration：`0022_workflow_trigger` 为 head。
- Real API：23 passed。
- Frontend：13 test files / 52 tests passed，production build passed。
- Browser：Desktop Chrome 3 passed。

上述结果是历史 Acceptance 证据，不代表本次规划更新重新执行。

## 8. 当前阶段

**Phase 1.9 已正式关闭。Phase 2.1 已正式立项，当前仅执行 2.1-A Product / Backend Contract。**

2.1-A 必须先冻结：

- Organization ↔ Tenant 关系；
- Membership 生命周期；
- Owner/Admin/Member 权限矩阵；
- 多组织归属策略；
- User/Tenant/Role 兼容迁移策略；
- API schema / error / pagination / idempotency；
- Resource scope 与 Audit 规则。

未冻结前不得直接实现 Migration / Service / UI。

## 9. 明确不自动转化为任务的边界

- MQ / Kafka / 通用 Event Bus。
- Temporal / Airflow 等分布式 Workflow Engine。
- 复杂 DAG、Saga、复杂 Policy DSL。
- Multi-Agent orchestration。
- 可视化拖拽 Workflow Designer。
- 任意代码执行平台。
- SSO / OIDC / SAML / SCIM 等完整企业 IAM。

这些只有进入正式 Phase 后才成为开发任务。
