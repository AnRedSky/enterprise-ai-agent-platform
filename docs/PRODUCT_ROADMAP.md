# 企业级 AI Agent Platform 产品整体实现路线

> 基线：`main` @ `89fab7adfe9d29fcfa1ef9c62da896e83448c9c9`
> 评估日期：2026-08-22
> 目的：在 Phase 1.9 与 Phase 2.1 正式关闭后，以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
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

Phase 1.9 与 Phase 2.1 已证明 Runtime、Workflow、Trigger、Governance、Organization、前后端链路具备稳定工程基线。因此后续路线优先补齐“企业知识质量、模型治理、调度可靠性”等运营能力，而不是重复扩展已关闭 Phase。

## 2. 当前基线判断

### 已完成并保持稳定

- Auth / RBAC / Tenant scope
- Organization / Membership / Organization Governance
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

### 已确认但尚未完成的能力缺口

1. Retrieval Production Quality：真实 Embedding Provider 的语义质量尚未形成生产质量 Contract。
2. Model Provider Governance：Provider 路由、Fallback、模型白名单、成本/用量治理尚未形成正式 Contract。
3. Scheduler Durability：当前 Scheduler 没有完整 `next_run_at`、lease、misfire policy、独立 scheduler state。
4. Workflow Orchestration Depth：当前不支持复杂 DAG、并行/条件分支、Saga、复杂 Policy DSL、可视化 Designer。
5. Event Infrastructure：没有通用 MQ/Kafka/Event Bus；当前 Webhook 是受控 HTTP 入口。
6. Multi-Agent：尚未形成正式的多 Agent 协作 Product Contract。
7. Agent Marketplace / 发布生态：当前 Agent 已版本化和治理，但尚未形成完整企业资产分发/复用产品。

## 3. 优先级路线

| 优先级 | 后续阶段 | 产品主题 | 企业场景 | 进入条件 |
|---|---|---|---|---|
| P0 | Phase 2.1 | Enterprise Organization & Access Governance | 企业管理员需要管理组织、成员、角色和资源边界 | 已完成并正式关闭 |
| P0 | **Phase 2.2** | **Retrieval Production Quality** | 企业知识问答需要稳定、可量化的真实语义检索质量 | 明确 Provider、数据集、Recall/Precision/Citation 指标 |
| P1 | Phase 2.3 | Model Provider Governance | 企业需要 Provider 路由、Fallback、模型白名单、成本/用量治理 | 明确成本口径、路由策略与 Provider Contract |
| P1 | Phase 2.4 | Durable Scheduler | 企业任务需要长期运行、故障恢复、misfire 与多实例语义 | 明确 scheduler lease / misfire / next-run Contract |
| P1 | Phase 2.5 | Advanced Workflow Orchestration | 企业流程需要并行、条件、重试分支、人工节点或补偿 | 明确 Workflow DSL 与执行语义，不能直接引入重量级 Engine |
| P2 | Phase 2.6 | Enterprise Integration / Event Infrastructure | 企业系统需要稳定事件集成、异步解耦和高吞吐事件处理 | 只有 Webhook 无法满足真实吞吐/可靠性需求时立项 |
| P2 | Phase 2.7 | Multi-Agent Collaboration | 复杂任务需要多个专职 Agent 协同 | 先有明确业务场景、协作协议、权限与成本边界 |
| P2 | Phase 2.8 | Agent Asset / Marketplace | 企业需要 Agent 模板复用、发布、共享和生命周期管理 | 明确资产所有权、版本、审批和跨组织共享模型 |

## 4. 当前正式开发阶段：Phase 2.2

### 目标

建立可量化、可重复、可审计的 Retrieval Production Quality Contract，使真实 Embedding Provider 的检索质量能够通过固定数据集和明确指标验收。

### 首个企业场景

> 企业知识库内容不断增长后，管理员需要能够回答“当前真实检索是否找到了正确内容、引用是否正确、Provider 替换后质量是否下降”，而不是只依赖人工主观判断。

### 首阶段范围

- 真实 Embedding Provider Contract。
- 可版本化评测数据集。
- Recall@K / Precision@K 基础指标。
- Citation correctness / source attribution 指标。
- Provider 与数据集的评测矩阵。
- 可重复的本地评估命令与结果记录。
- Real Provider Quality Gate。
- 与现有 Knowledge / RAG Retrieval 链路的质量边界。

### 明确不直接纳入 2.2-A

- 不先实现新的 Provider SDK。
- 不因为指标缺失直接更换现有 Retrieval 架构。
- 不引入 MQ/Kafka/Temporal 等无关基础设施。
- 不把 Mock embedding 结果当作真实 Provider 质量结论。
- 不在 Contract 未冻结前设计数据库 Migration。

## 5. 后续阶段统一验收标准

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

对于 Retrieval Quality，额外必须回答：

11. 评测数据集如何版本化？
12. Recall / Precision / Citation 的计算定义是什么？
13. 最低质量门槛是什么？
14. Provider 替换或模型变更如何进行回归比较？

## 6. 风险控制

- 不因为历史 `HISTORICAL_PHASE_*` 文档重新启用旧 Phase 编号。
- 不直接把 MQ/Kafka、Temporal、复杂 DAG、Multi-Agent 等技术名词变成产品需求。
- 不修改已通过的 Runtime Reliability / Organization Governance 边界来“顺便支持”新能力。
- 新增数据库字段/表必须先设计 Migration，再实现依赖代码。
- 真实 Provider 的质量结论必须来自本地真实 Provider 验证，不得用 Mock 结果代替。
- 每个 Phase 完成后必须同步 Phase、Acceptance、Project Status、错误记录。

## 7. 当前执行结论

**Phase 2.1 已正式关闭；当前正式进入 Phase 2.2：Retrieval Production Quality。第一项开发任务为 2.2-A Product / Retrieval Quality Contract。**
