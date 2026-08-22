# 产品需求与功能开发对比矩阵

> 基线：`main` @ `f986577fbe78e3aa8c47c2478e7f1c75c424eacc`
> 目的：将“产品能力目标、当前实现、验收证据、明确缺口、下一步决策”放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 总体对比

| 产品域 | 产品目标 | 当前实现 | 验收状态 | 差距 | 下一动作 |
|---|---|---|---|---|---|
| Identity / RBAC | 企业用户、角色、Tenant 隔离 | Auth、RBAC、Tenant scope | 已验收当前范围 | Organization / Membership / 企业 IAM 未完整形成 | **Phase 2.1** |
| Agent | 可配置、版本化、可治理 Agent | Agent + Version + Owner/RBAC | 已覆盖当前范围 | Marketplace、发布生态未形成 | Phase 2.8 候选 |
| Runtime | 稳定执行 Agent | Runtime + Session + Context + Model/Tool/Knowledge/Memory | 已验收 | 更复杂 orchestration 未定义 | 保持基线 |
| Model Gateway | Provider-neutral LLM 接入 | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 路由/Fallback/成本治理待产品决策 | Phase 2.3 候选 |
| Tool Runtime | 安全、可审计工具调用 | Registry/Binding/Schema/HTTP Executor/Audit | 已覆盖当前范围 | 通用代码执行明确禁止 | 保持边界 |
| Memory | Session/用户/Agent 可见记忆 | PostgreSQL MemoryRecord/Service | 已覆盖当前范围 | 向量记忆、自动摘要等未纳入 | 产品需求后再立项 |
| Observability | 可查询、可追踪、可审计 | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 分布式 Observability 平台未定义 | 保持基线 |
| Knowledge | 企业文档知识库 | KB/Document/Version/Chunk/Ingestion | 已覆盖当前范围 | 真实生产质量需验证 | Phase 2.2 联动 |
| Retrieval | 高质量企业检索 | Lexical/Vector/Hybrid/Citation/Debug/Evaluation | 已覆盖工程链路 | 真实 Embedding Provider 质量尚无生产 Contract | **Phase 2.2** |
| Workflow | 可治理流程执行 | Definition/Version/Publish/Execution | 已验收 | 复杂 DAG/Saga/Engine 未实现 | Phase 2.5 候选 |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已形成闭环 | 已验收 | Organization scope 仍不足 | Phase 2.1 |
| Circuit Breaker | Provider/Workflow 失败隔离 | CLOSED/OPEN/HALF_OPEN + persistence/drift | 已验收 | 无明确新缺口 | 只维护回归 |
| Manual Trigger | API 业务入口 | CRUD/Invoke/Lifecycle | 已验收 | 无明确新缺口 | 保持 |
| Scheduled Trigger | 时间驱动 Workflow | interval Scheduler + idempotency + recovery | 已验收 | 无 lease/misfire/next_run_at | Phase 2.4 候选 |
| Webhook Trigger | 外部事件驱动 Workflow | Secret/Auth/Event identity/Idempotency | 已验收 | 通用 Event Bus 未实现 | Phase 2.6 候选 |
| Frontend | 管理、配置、调试 | Vue 3 + API Types + Governance UI | 已验收当前范围 | Organization 管理体验待补 | Phase 2.1 |
| Browser E2E | 真实用户链路验证 | Playwright Browser → Vue → Backend | 已验收 | 新功能需新增独立 E2E | 随 Phase 2.1 开始 |

## 2. Phase 与产品能力映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 1.0 | 项目初始化 / 最小基础 | 已完成 | 否 |
| 1.2 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础 | 已完成 | 否 |
| 1.3 | Model Gateway、Tool Runtime、Memory、Observability | 已完成当前历史范围 | 否，除新需求/回归 |
| 1.4 | Knowledge / RAG / Retrieval | 已完成当前历史范围 | 真实 Provider 质量进入 2.2 时再扩展 |
| 1.5 | Workflow / Governance / Reliability / Circuit Breaker | 正式关闭 | 否，除新需求/回归 |
| 1.6 | Trigger Contract / Frontend / Browser | 正式关闭 | 否，除新需求/回归 |
| 1.7 | Scheduled Trigger / Scheduler | 正式关闭 | Durable Scheduler 进入 2.4 时再扩展 |
| 1.8 | Webhook / Event Trigger | 正式关闭 | Event Infrastructure 进入 2.6 时再评估 |
| 1.9 | Runtime Reliability / Production Hardening | 正式关闭 | 否，除新需求/回归 |
| **2.1** | **Enterprise Organization & Access Governance** | **已立项 / 待开发** | **是，当前阶段** |
| 2.2 | Retrieval Production Quality | 路线已定义 / 待立项实施 | 后续 |
| 2.3 | Model Provider Governance | 候选路线 | 需求确认后 |
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

Phase 1.9 已达到 P5；Phase 2.1 尚未进入 P2 以后，不得提前标记完成。

## 4. 当前已确认的开发缺口

### G-01 文档基线一致性

历史文档可能存在旧 Phase 描述；当前阶段以 `PROJECT_STATUS.md` 为唯一状态入口，产品路线以 `PRODUCT_ROADMAP.md` 为规划入口。

### G-02 Enterprise Organization / IAM

当前已有 Auth/RBAC/Tenant scope，但 `User` 直接绑定 Tenant、`Role` 全局唯一、`UserRole` 直接关联用户与角色，尚不足以表达企业 Organization / Membership 生命周期。Phase 2.1 已正式立项。

### G-03 真实 Retrieval Provider 质量

需要独立数据集、真实 Provider、指标和 Acceptance；Mock Quality Gate 不能替代生产语义质量。

### G-04 Scheduler 产品化边界

当前 Scheduler 没有 `next_run_at`、lease、misfire、独立 scheduler state；只有真实需求确认后进入 Phase 2.4。

### G-05 Workflow 编排深度

当前 Workflow 已完成串行 Runtime 与 Trigger 治理；复杂 DAG、并行、条件分支、Saga、Policy DSL、Designer 进入 Phase 2.5 前必须冻结执行语义。

### G-06 Event Infrastructure

当前没有通用 MQ/Kafka/Event Bus。Phase 2.6 只有在真实业务吞吐/解耦需求证明 Webhook 不足时才进入实施。

### G-07 Multi-Agent

尚未形成正式 Product Contract。进入 2.7 前必须定义协作协议、权限、状态、成本和失败语义。

### G-08 Model Governance / Agent Marketplace

属于产品路线候选，不得直接按技术愿望开发；分别进入 2.3 / 2.8 前先完成需求与架构 Contract。

## 5. Phase 2.1 当前任务

**2.1-A Product / Backend Contract**

必须先冻结：

1. Organization ↔ Tenant 关系。
2. Membership 生命周期。
3. Owner/Admin/Member 权限矩阵。
4. 多组织归属策略。
5. 现有 User/Tenant/Role 数据迁移兼容策略。
6. API schema、错误码、分页、幂等性。
7. 资源访问 scope 与 Audit 规则。

Contract 未冻结前不得实现 Migration / Service / UI。

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

截至 `f1758e0`，Phase 1.9 已关闭，项目从“Runtime 工程闭环”进入“企业产品化能力补齐”阶段。下一正式开发阶段已经确定为 **Phase 2.1 Enterprise Organization & Access Governance**；其余 2.2～2.8 是按企业价值排序的路线，不等同已经完成需求冻结。
