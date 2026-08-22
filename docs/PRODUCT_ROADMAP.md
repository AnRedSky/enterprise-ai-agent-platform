# 企业级 AI Agent Platform 产品整体实现路线

> 基线：`main` @ `f1758e0a76ad18ad607e6adaa764bc8b017a58bf`
> 评估日期：2026-08-22
> 目的：在 Phase 1.9 正式关闭后，以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
> 规则：本路线是产品规划基线；只有已进入对应 Phase 的范围才允许转化为开发任务。

## 1. 产品目标

平台目标不是继续堆叠 Agent Runtime 功能，而是逐步成为企业可实际运营的 AI 应用基础平台：

```text
企业身份与组织
 → AI 资产治理
 → Agent / Workflow / Knowledge
 → 安全执行与可靠性
 → 真实业务集成
 → 运营、成本、质量与审计
 → 多 Agent / 高级编排（按真实需求进入）
```

Phase 1.9 已证明当前 Runtime、Workflow、Trigger、Governance 与前后端链路具备稳定工程基线。因此后续路线优先补齐“企业能否真正接入、管理、运营”的能力，而不是重复扩展已关闭 Phase。

## 2. 当前基线判断

### 已完成并保持稳定

- Auth / RBAC / Tenant scope
- Agent / Version / Runtime / Session
- Model Gateway
- Tool Registry / Secure HTTP Tool Runtime
- Memory
- Observability / Audit / Trace
- Knowledge / RAG / Retrieval 工程链路
- Workflow / Execution Governance / Reliability / Circuit Breaker
- Manual / Scheduled / Webhook Trigger
- Vue 管理与调试界面
- Real API 与 Browser E2E 验收闭环

### 已确认但尚未形成新 Phase 的缺口

1. Enterprise IAM / Organization：当前 Tenant + RBAC 不等同企业组织、成员生命周期和组织级权限管理。
2. Retrieval Production Quality：真实 Embedding Provider 的语义质量尚未形成生产质量 Contract。
3. Scheduler Durability：当前 Scheduler 没有 `next_run_at`、lease、misfire policy、独立 scheduler state。
4. Workflow Orchestration Depth：当前不支持复杂 DAG、并行/条件分支、Saga、复杂 Policy DSL、可视化 Designer。
5. Event Infrastructure：没有通用 MQ/Kafka/Event Bus；当前 Webhook 是受控 HTTP 入口。
6. Multi-Agent：尚未形成正式的多 Agent 协作 Product Contract。
7. Model Governance：Provider 路由、Fallback、成本治理属于待产品决策的长期能力。
8. Agent Marketplace / 发布生态：当前 Agent 已版本化和治理，但尚未形成完整企业资产分发/复用产品。

其中 1～6 是当前文档明确确认的能力边界；7～8 属于基于现有产品目标的候选方向，进入开发前必须补充产品需求与架构决策。

## 3. 优先级路线

| 优先级 | 后续阶段 | 产品主题 | 企业场景 | 进入条件 |
|---|---|---|---|---|
| P0 | Phase 2.1 | Enterprise Organization & Access Governance | 企业管理员需要管理组织、成员、角色和资源边界 | 已具备现有 Tenant/User/RBAC 基础，可形成明确 Contract |
| P0 | Phase 2.2 | Retrieval Production Quality | 企业知识问答需要稳定、可量化的真实语义检索质量 | 明确 Provider、数据集、Recall/Precision/Citation 指标 |
| P1 | Phase 2.3 | Model Provider Governance | 企业需要 Provider 路由、Fallback、模型白名单、成本/用量治理 | 明确成本口径、路由策略与 Provider Contract |
| P1 | Phase 2.4 | Durable Scheduler | 企业任务需要长期运行、故障恢复、misfire 与多实例语义 | 明确 scheduler lease / misfire / next-run Contract |
| P1 | Phase 2.5 | Advanced Workflow Orchestration | 企业流程需要并行、条件、重试分支、人工节点或补偿 | 明确 Workflow DSL 与执行语义，不能直接引入重量级 Engine |
| P2 | Phase 2.6 | Enterprise Integration / Event Infrastructure | 企业系统需要稳定事件集成、异步解耦和高吞吐事件处理 | 只有 Webhook 无法满足真实吞吐/可靠性需求时立项 |
| P2 | Phase 2.7 | Multi-Agent Collaboration | 复杂任务需要多个专职 Agent 协同 | 先有明确业务场景、协作协议、权限与成本边界 |
| P2 | Phase 2.8 | Agent Asset / Marketplace | 企业需要 Agent 模板复用、发布、共享和生命周期管理 | 明确资产所有权、版本、审批和跨组织共享模型 |

> **排序原则**：先解决企业“谁能使用、谁负责、谁能看到什么”，再解决“知识是否足够准确”，随后解决“模型成本与可靠性”，最后扩展高级编排、事件基础设施和 Multi-Agent。这样可以避免在组织和治理基础不足时扩张 Runtime 复杂度。

## 4. Phase 2.1 作为下一项正式开发

### 目标

建立企业级 Organization / Membership 基础 Contract，在现有 Tenant / User / Role 模型之上增加组织管理语义，但不在本阶段引入 SSO / SCIM 等完整 IAM 产品。

### 首个企业场景

> 企业管理员创建组织后，可以邀请/管理成员，将成员加入组织角色；普通成员只能访问自己有权限的 Agent、Workflow、Knowledge 等资源；组织管理员可以进行成员与角色管理；所有管理操作可审计。

### 本阶段范围

- Organization 基础实体与生命周期。
- Organization Member / Membership。
- 组织级角色与权限绑定模型。
- 成员激活/停用。
- Owner/Admin/Member 的明确后端权限边界。
- 资源访问继续由 Backend Service + Tenant/Organization scope 决定。
- 管理 API 与最小 Vue 管理界面。
- Audit / Trace 关联。

### 明确不纳入 Phase 2.1

- SSO / OIDC / SAML。
- SCIM 自动同步。
- HR / AD / LDAP 集成。
- 跨组织资源共享。
- ABAC / Policy DSL。
- 完整企业 IAM 产品。

## 5. 后续阶段的统一验收标准

所有进入正式 Phase 的能力至少回答：

1. 企业用户是谁？
2. 业务场景和 KPI 是什么？
3. Backend Contract 是什么？
4. Tenant / Organization / RBAC 边界是什么？
5. 数据模型和 Migration 是什么？
6. Failure / Retry / Timeout / Idempotency 是什么？
7. Audit / Trace 如何追踪？
8. Real API 如何证明真实数据库/Redis/Provider 链路？
9. 是否需要 Frontend 与 Browser E2E？
10. Acceptance 如何关闭？

## 6. 风险控制

- 不因为历史 `HISTORICAL_PHASE_*` 文档重新启用旧 Phase 编号。
- 不直接把 MQ/Kafka、Temporal、复杂 DAG、Multi-Agent 等技术名词变成产品需求。
- 不修改已通过的 Runtime Reliability 边界来“顺便支持”新能力。
- 新增数据库字段/表必须先设计 Migration，再实现依赖代码。
- 真实 Provider 的质量结论必须来自本地真实 Provider 验证，不得用 Mock 结果代替。
- 每个 Phase 完成后必须同步 Phase、Acceptance、Project Status、错误记录。

## 7. 当前执行结论

**下一开发阶段正式确定为 Phase 2.1：Enterprise Organization & Access Governance。**

第一项开发任务为：**Phase 2.1-A Product / Backend Contract：定义 Organization、Membership、角色继承/覆盖边界以及现有 Tenant/User/RBAC 的兼容迁移策略。**

该任务完成 Contract 和验收标准后，才进入 Database Migration 与 Backend Domain 实现。
