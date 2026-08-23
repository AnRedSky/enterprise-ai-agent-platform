# 企业级 AI Agent Platform 产品整体实现路线

> 基线：当前 `main`
> 评估日期：2026-08-23
> 目的：以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
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

## 2. 当前基线判断

### 已完成并保持稳定

- Auth / RBAC / Tenant / Organization scope
- Agent / Version / Runtime / Session
- Model Gateway 基础 Contract
- Tool Registry / Secure HTTP Tool Runtime
- Memory
- Observability / Audit / Trace
- Knowledge / RAG / Retrieval 工程链路
- Workflow / Execution Governance / Reliability / Circuit Breaker
- Manual / Scheduled / Webhook Trigger 基础能力
- Vue 管理与调试界面
- Real API 与 Browser E2E 历史验收闭环
- Model Provider / Profile Governance
- Provider routing / governed fallback / fallback policy
- Durable model usage / cost accounting

### 当前正式阶段

**无进行中的正式 Phase。Phase 2.3 Model Provider Governance 已完成并正式关闭。**

### 候选能力缺口

1. Scheduler Durability：当前 Scheduler 尚没有完整 `next_run_at`、lease、misfire policy、独立 scheduler state Contract。
2. Workflow Orchestration Depth：当前不支持复杂 DAG、并行/条件分支、Saga、复杂 Policy DSL、可视化 Designer。
3. Event Infrastructure：没有通用 MQ/Kafka/Event Bus；当前 Webhook 是受控 HTTP 入口。
4. Multi-Agent / Marketplace：尚未形成正式 Product Contract。

## 3. 优先级路线

| 优先级 | 后续阶段 | 产品主题 | 企业场景 | 进入条件 |
|---|---|---|---|---|
| P0 | Phase 2.1 | Enterprise Organization & Access Governance | 企业管理员需要管理组织、成员、角色和资源边界 | 已完成并正式关闭 |
| P0 | Phase 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 企业需要稳定检索质量，并能够明确选择和追踪实际模型 | 已完成并正式关闭 |
| P1 | Phase 2.3 | Model Provider Governance | 企业需要 Provider 路由、Fallback、模型白名单、成本/用量治理 | 已完成并正式关闭 |
| **P1** | **Phase 2.4** | **Durable Scheduler** | **企业任务需要长期运行、故障恢复、misfire 与多实例语义** | **明确 scheduler lease / misfire / next-run Contract** |
| P1 | Phase 2.5 | Advanced Workflow Orchestration | 企业流程需要并行、条件、重试分支、人工节点或补偿 | 明确 Workflow DSL 与执行语义 |
| P2 | Phase 2.6 | Enterprise Integration / Event Infrastructure | 企业系统需要稳定事件集成、异步解耦和高吞吐事件处理 | Webhook 无法满足真实吞吐/可靠性需求时立项 |
| P2 | Phase 2.7 | Multi-Agent Collaboration | 复杂任务需要多个专职 Agent 协同 | 明确业务场景、协作协议、权限与成本边界 |
| P2 | Phase 2.8 | Agent Asset / Marketplace | 企业需要 Agent 模板复用、发布、共享和生命周期管理 | 明确资产所有权、版本、审批和跨组织共享模型 |

## 4. Phase 2.3 关闭结果

Phase 2.3 已完成：

- Provider/Profile routing Contract 与真实 PostgreSQL resolver；
- Runtime governed invocation；
- connectivity / timeout / rate limit / provider 5xx fallback；
- `FallbackPolicy` 强制执行与最大 attempts=2；
- provider attempt usage identity 与 Workflow Trace；
- `model_usage_records` PostgreSQL durable accounting；
- pricing source/version 与 deterministic cost calculation；
- organization scoped usage query；
- Secret / endpoint / credential_ref 边界；
- 本地 targeted、Backend regression、Migration 与 Tenant Safe Real API acceptance。

## 5. Phase 2.4 进入条件

Phase 2.4 目前仅为候选路线。正式进入代码开发前必须先确认：

1. `next_run_at` 的计算、时区与时钟语义；
2. 多实例 scheduler lease / ownership 语义；
3. lease 过期、抢占与重复执行边界；
4. misfire policy 与可接受延迟；
5. 执行幂等键与重复触发语义；
6. paused / enabled / disabled 状态转换；
7. 调度状态与 WorkflowExecution 的审计、trace 关系；
8. PostgreSQL migration 与 Real API acceptance 场景。

上述 Contract 未确认前，不将 Scheduler 技术实现直接转化为产品需求，也不创建对应 Migration 或业务代码。

## 6. 后续阶段统一验收标准

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

## 7. 风险控制

- 不重新启用历史 `HISTORICAL_PHASE_*` 文档。
- 不直接把 MQ/Kafka、Temporal、复杂 DAG、Multi-Agent 等技术名词变成产品需求。
- 不修改已通过的 Runtime Reliability / Organization Governance 边界来“顺便支持”新能力。
- 新增数据库字段/表必须先设计 Migration，再实现依赖代码。
- 真实 Provider 的质量结论必须来自本地真实 Provider 验证，不得用 Mock 结果代替。
- 每个正式 Phase 完成后必须同步 Phase、Acceptance、Project Status、错误记录。

## 8. 当前执行结论

**Phase 2.3 已关闭。下一正式工作不是直接编码 Scheduler，而是确认 Phase 2.4 Durable Scheduler Contract；Contract 通过后再按开发准则进入 Backend Domain + API Contract → Migration → tests → Real API Gate。**
