# 企业级 AI Agent Platform 产品整体实现路线

> 基线：`main`
> 评估日期：2026-08-28
> 目的：以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
> 规则：只有已进入正式 Phase 的范围才允许转化为开发任务；候选路线必须先完成 Contract 决策。

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
- Durable Scheduler
- Advanced Workflow Orchestration：Conditional Branching、Multi-frontier、Durable Resume、Recovery / Replay Closure、Worker fencing、Frontier terminalization 与 checkpoint lifecycle guard

### 当前正式阶段

**Phase 2.7 Advanced Workflow Orchestration 主线生产实现已完成；当前正在执行本地回归、Migration / Real API / 前端与 E2E 验收。Phase 2.8-A Multi-Agent Collaboration Contract 已进入 Contract 冻结。**

### 候选能力缺口

1. Event Infrastructure：没有通用 MQ/Kafka/Event Bus；当前 Webhook 是受控 HTTP 入口。
2. Multi-Agent Collaboration：需要受治理的 Agent Delegation、上下文隔离、预算、权限、审计和可靠性边界。
3. Agent Asset / Marketplace：需要明确资产所有权、版本、审批和跨组织共享模型。

## 3. 优先级路线

| 优先级 | 后续阶段 | 产品主题 | 企业场景 | 当前决策 |
|---|---|---|---|---|
| P0 | Phase 2.1 | Enterprise Organization & Access Governance | 企业管理员需要管理组织、成员、角色和资源边界 | 已完成并正式关闭 |
| P0 | Phase 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 企业需要稳定检索质量，并能够明确选择和追踪实际模型 | 已完成并正式关闭 |
| P1 | Phase 2.3 | Model Provider Governance | 企业需要 Provider 路由、Fallback、模型白名单、成本/用量治理 | 已完成并正式关闭 |
| P1 | Phase 2.4 | Durable Scheduler | 企业任务需要长期运行、故障恢复、misfire 与多实例语义 | 已实现并完成主线收口 |
| P1 | Phase 2.5 | Scheduler → Worker Execution Decoupling | Scheduler 与执行 Worker 需要独立生命周期和故障边界 | 已完成并正式关闭 |
| P1 | Phase 2.6 | Durable Execution Checkpoint Foundation | 长流程执行需要 checkpoint、resume、DAG continuation | 已完成并正式关闭 |
| P1 | Phase 2.7 | Advanced Workflow Orchestration | 企业流程需要条件分支、并行 Frontier、恢复、Replay 与可靠终止 | 主线生产实现已完成，当前验收收口 |
| **P1** | **Phase 2.8** | **Multi-Agent Collaboration** | **复杂业务需要多个受治理 Agent 协同完成子任务** | **先执行 Phase 2.8-A Contract 冻结，再进入 Backend 实现** |
| P2 | Phase 2.9 | Enterprise Integration / Event Infrastructure | 企业系统需要稳定事件集成、异步解耦和高吞吐事件处理 | Multi-Agent 后评估；Webhook 无法满足真实吞吐/可靠性需求时再立项 |
| P2 | Phase 2.10 | Agent Asset / Marketplace | 企业需要 Agent 模板复用、发布、共享和生命周期管理 | 明确资产所有权、版本、审批和跨组织共享模型后再立项 |

## 4. Phase 2.8 进入条件

Phase 2.8 首版采用 **Contract-first + MVP 边界 + 复用现有 Durable Execution / Governance 能力**：

- 首版只支持一次 Workflow Execution 内受治理的 Agent Delegation；
- Delegation 必须绑定 tenant、source execution、source agent version、target agent version；
- 使用稳定 `delegation_key` 实现持久化幂等；
- Worker Agent 只获得显式声明的输入与上下文引用，不复制父 Execution 全量上下文；
- 必须限制 delegation depth、active delegation count、timeout 与模型预算；
- 必须复用现有 RBAC / tenant / Model Provider / Profile Governance；
- Worker 成功/失败/超时/取消必须形成独立 Durable Delegation 状态，但不得复制第二套 Workflow Retry / Recovery 状态机；
- Audit / Trace 必须形成 source execution → delegation → worker execution 的可反查链路；
- 不提前引入 MQ/Kafka、Marketplace、跨 tenant Agent 调用、无限递归 spawning 或独立可靠性框架。

详细 Contract：`docs/02-phases/PHASE_2_8_A_CONTRACT.md`。

## 5. Phase 2.8 代码开发顺序

Contract 冻结并通过审查后，严格按：

```text
Backend Domain + API Contract
        ↓
PostgreSQL Migration
        ↓
Unit / Integration / API Contract
        ↓
Real API Gate
        ↓
Backend Regression Gate
        ↓
Frontend API Types + Vitest / UI（如范围需要）
        ↓
Browser E2E（如范围需要）
        ↓
Acceptance / Status / Error
```

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
- 不直接把 MQ/Kafka、Temporal 等技术名词变成产品需求。
- 不修改已通过的 Runtime Reliability / Organization Governance / Durable Workflow 边界来“顺便支持”新能力。
- 新增数据库字段/表必须先设计 Migration，再实现依赖代码。
- 真实 Provider 的质量结论必须来自本地真实 Provider 验证，不得用 Mock 结果代替。
- 每个正式 Phase 完成后必须同步 Phase、Acceptance、Project Status、错误记录。

## 8. 当前执行结论

**Phase 2.7 主线生产实现已完成。开发者于 2026-08-28 实际执行 Backend targeted、Phase 2.7 targeted regression、完整 Unit regression 与 `uv run pytest -q`，全部通过且 RuntimeWarning gate 无警告。下一工程任务为完成 Phase 2.7 的 Migration / Real API / 前端 / E2E 本地验收，同时启动 Phase 2.8-A Multi-Agent Collaboration Contract 冻结；Contract 未通过前不创建 Multi-Agent 生产实现。**
