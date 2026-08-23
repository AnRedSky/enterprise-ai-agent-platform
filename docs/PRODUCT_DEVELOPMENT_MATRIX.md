# 产品需求与功能开发对比矩阵

> 基线：当前 `main`
> 目的：将“产品能力目标、当前实现、验收证据、明确缺口、下一步决策”放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 总体对比

| 产品域 | 产品目标 | 当前实现 | 验收状态 | 差距 | 下一动作 |
|---|---|---|---|---|---|
| Identity / RBAC | 企业用户、角色、Tenant 隔离 | Auth、RBAC、Tenant scope | 已验收当前范围 | Organization / Membership / 企业 IAM 已进入当前基线 | 保持基线 |
| Agent | 可配置、版本化、可治理 Agent | Agent + Version + Owner/RBAC | 已覆盖当前范围 | Marketplace、发布生态未形成 | Phase 2.8 候选 |
| Runtime | 稳定执行 Agent | Runtime + Session + Context + Model/Tool/Knowledge/Memory | 已验收 | Provider Governance runtime routing 待 2.3-B | Phase 2.3 |
| Model Gateway | Provider-neutral LLM 接入 | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 路由/Fallback/成本/用量治理待 2.3 实现 | Phase 2.3 |
| Model Provider / Profile | 模型供应商与模型身份可配置、选择、追踪、评估 | Provider/Profile 数据模型、CRUD API、Organization scope、Audit | **2.2-E 已验收** | 治理策略已形成 2.3-A executable contract，尚未接入 Runtime | 2.3-B |
| Tool Runtime | 安全、可审计工具调用 | Registry/Binding/Schema/HTTP Executor/Audit | 已覆盖当前范围 | 通用代码执行明确禁止 | 保持边界 |
| Memory | Session/用户/Agent 可见记忆 | PostgreSQL MemoryRecord/Service | 已覆盖当前范围 | 向量记忆、自动摘要等未纳入 | 产品需求后再立项 |
| Observability | 可查询、可追踪、可审计 | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 2.3 usage identity 接入待后续 | 2.3-B 后续 |
| Knowledge | 企业文档知识库 | KB/Document/Version/Chunk/Ingestion | 已覆盖当前范围 | 真实生产质量已由 2.2 覆盖 | 保持基线 |
| Retrieval | 高质量企业检索 | Lexical/Vector/Hybrid/Citation/Debug/Evaluation 工程链路 | 已验收 2.2 当前范围 | 无新的 2.2 功能扩展 | 保持基线 |
| Workflow | 可治理流程执行 | Definition/Version/Publish/Execution | 已验收 | 复杂 DAG/Saga/Engine 未实现 | Phase 2.5 候选 |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已形成闭环 | 已验收 | Provider routing/cost/usage governance 正进入 2.3 | Phase 2.3 |
| Circuit Breaker | Provider/Workflow 失败隔离 | CLOSED/OPEN/HALF_OPEN + persistence/drift | 已验收 | 与 2.3 fallback semantics 需保持清晰边界 | 2.3 回归 |
| Manual Trigger | API 业务入口 | CRUD/Invoke/Lifecycle | 已验收 | 无明确新缺口 | 保持 |
| Scheduled Trigger | 时间驱动 Workflow | interval Scheduler + idempotency + recovery | 已验收 | 无 lease/misfire/next_run_at | Phase 2.4 候选 |
| Webhook Trigger | 外部事件驱动 Workflow | Secret/Auth/Event identity/Idempotency | 已验收 | 通用 Event Bus 未实现 | Phase 2.6 候选 |
| Frontend | 管理、配置、调试 | Vue 3 + API Types + Governance UI | 已验收当前范围 | 2.3 Provider routing/cost UI 尚未立项到实现 | 按 2.3-B/F 裁剪 |
| Browser E2E | 真实用户链路验证 | Playwright Browser → Vue → Backend | 已验收 | 2.3 若新增用户链路再增加专项 E2E | 随 UI 进入 |

## 2. Phase 与产品能力映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 1.0 | 项目初始化 / 最小基础 | 已完成 | 否 |
| 1.2 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础 | 已完成 | 否 |
| 1.3 | Model Gateway、Tool Runtime、Memory、Observability | 已完成当前历史范围 | 否，除新需求/回归 |
| 1.4 | Knowledge / RAG / Retrieval | 已完成当前历史范围 | 真实 Provider 质量进入 2.2 时扩展 |
| 1.5 | Workflow / Governance / Reliability / Circuit Breaker | 正式关闭 | 否，除新需求/回归 |
| 1.6 | Trigger Contract / Frontend / Browser | 正式关闭 | 否，除新需求/回归 |
| 1.7 | Scheduled Trigger / Scheduler | 正式关闭 | Durable Scheduler 进入 2.4 时再扩展 |
| 1.8 | Webhook / Event Trigger | 正式关闭 | Event Infrastructure 进入 2.6 时再评估 |
| 1.9 | Runtime Reliability / Production Hardening | 正式关闭 | 否，除新需求/回归 |
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除新需求/回归 |
| **2.2** | **Retrieval Production Quality + 2.2-E Model Provider/Profile Foundation** | **正式关闭** | 否，除回归 |
| **2.3** | **Model Provider Governance（路由/Fallback/成本/用量）** | **2.3-A Contract 已实现，2.3-B 进行中** | **是** |
| 2.4 | Durable Scheduler | 候选路线 | 需求确认后 |
| 2.5 | Advanced Workflow Orchestration | 候选路线 | 需求确认后 |
| 2.6 | Enterprise Event Infrastructure | 候选路线 | 需求确认后 |
| 2.7 | Multi-Agent Collaboration | 候选路线 | 需求确认后 |
| 2.8 | Agent Asset / Marketplace | 候选路线 | 需求确认后 |

## 3. 当前产品“完成”的判定标准

### P0 — 产品能力存在
代码已经提供领域对象、Service、API 或 UI 能力。

### P1 — Contract 完整
Backend API Contract、权限、Tenant、错误码、生命周期、数据模型边界已经明确。

### P2 — 自动化测试覆盖
Backend pytest / Frontend Vitest / 必要 Integration 与 API Contract tests 已覆盖关键行为。

### P3 — Real API 验证
真实 PostgreSQL/Redis/HTTP/Provider 边界按任务要求实际执行，而不是只运行 Mock。

### P4 — Browser E2E
涉及前后端用户链路时，通过真实 Browser → Vue → Backend HTTP 验证。

### P5 — Acceptance / Status 关闭
对应 Phase Acceptance、Project Status、错误记录已经同步，任务正式关闭。

2.3-A 当前为 **P0/P1 + unit contract implementation**；targeted test 尚未由开发者实际执行，因此不得标记为 Passed。

## 4. 当前已确认的开发缺口

### G-01 文档基线一致性

历史文档可能存在旧 Phase 描述；当前阶段以 `PROJECT_STATUS.md` 为状态入口，产品路线以 `PRODUCT_ROADMAP.md` 为规划入口。

### G-02 Enterprise Organization / IAM

当前已有 Auth/RBAC/Tenant/Organization/Membership scope；Phase 2.1 已关闭。

### G-03 真实 Retrieval Provider 质量

2.2 已完成当前定义范围，后续只维护回归。

### G-04 Model Provider / Model Profile

2.2-E 已完成 Provider/Profile 数据模型、Organization scoped CRUD、credential reference、Audit、Runtime/Evaluation profile foundation 与 Frontend/Browser acceptance。2.3 继续在其上实现治理策略，但不得修改 2.2 foundation 来绕过 Contract。

### G-05 Scheduler 产品化边界

当前 Scheduler 没有 `next_run_at`、lease、misfire、独立 scheduler state；只有真实需求确认后进入 Phase 2.4。

### G-06 Workflow 编排深度

当前 Workflow 已完成串行 Runtime 与 Trigger 治理；复杂 DAG、并行、条件分支、Saga、Policy DSL、Designer 进入 Phase 2.5 前必须冻结执行语义。

### G-07 Event Infrastructure

当前没有通用 MQ/Kafka/Event Bus。Phase 2.6 只有在真实业务吞吐/解耦需求证明 Webhook 不足时才进入实施。

### G-08 Multi-Agent / Marketplace

尚未形成正式 Product Contract。进入 2.7/2.8 前必须先完成需求与架构 Contract。

## 5. 当前正式任务

**Phase 2.3-A Provider Governance Contract 已实现；当前正式任务为 2.3-B Backend Domain + API Contract。**

2.3-A 已冻结：

1. Organization-scoped routing。
2. Explicit Profile / Organization Default 两种 routing strategy。
3. Fallback eligibility 与 bounded attempts。
4. Capability / provider allowlist constraints。
5. Cost unit、pricing source、pricing version。
6. Usage identity 与 audit trace dimensions。

2.3-B 必须先回答并实现：

1. Runtime 如何提交 routing request / profile identity。
2. Provider/Profile 候选如何从 PostgreSQL 实际解析。
3. Fallback candidate 如何保持 organization/capability/model-type 边界。
4. 哪些 routing/cost/usage fields 需要持久化；若需要必须先 Migration。
5. Runtime trace / Audit 如何写入 provider/profile/usage identity。

## 6. 后续任务拆解规则

```text
Task N-A 需求 / Product Contract
Task N-B Backend Domain + API Contract
Task N-C Database Migration + Backend Tests
Task N-D Real API / Integration Validation
Task N-E Frontend API Types + Vitest
Task N-F Frontend UI
Task N-G Backend Regression Gate
Task N-H Frontend Regression Gate
Task N-I Browser E2E
Task N-J Acceptance + Project Status + Error Records
```

若任务不涉及数据库、Frontend 或 Browser，则裁剪对应步骤并在 Phase 文档记录原因。

## 7. 结论

Phase 2.2 已关闭。当前正式工作为 **Phase 2.3 Model Provider Governance**；2.3-A 已形成可执行 Contract，但尚未宣称通过验收。下一开发动作是 2.3-B Backend Domain + API Contract，而不是继续整理文档或扩展已关闭的 Phase 2.2。
