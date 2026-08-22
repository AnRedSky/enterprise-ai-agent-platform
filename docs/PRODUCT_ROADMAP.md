# 企业级 AI Agent Platform 产品整体实现路线

> 基线：当前 `main`
> 评估日期：2026-08-22
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
- Manual / Scheduled / Webhook Trigger
- Vue 管理与调试界面
- Real API 与 Browser E2E 历史验收闭环

### 当前进行中

**Phase 2.2 Retrieval Production Quality**

其中 2.2-E 专门补齐 Model Provider / Model Profile Governance Foundation，为 Retrieval evaluation 与 Agent Runtime 提供受治理模型身份。

### 已确认但尚未完成的能力缺口

1. Retrieval Production Quality：真实 Embedding Provider 的语义质量尚未形成最终产品质量 Contract。
2. Runtime Model Profile Resolution：Agent / Chat 尚需从具体 model string 迁移到受治理 Profile identity。
3. Evaluation Model Profile Selection：evaluation runner 尚需支持 Profile identity 并将其写入 trace / baseline identity。
4. Model Provider Governance：Provider 路由、Fallback、模型白名单、成本/用量治理尚未形成正式 Contract。
5. Scheduler Durability：当前 Scheduler 没有完整 `next_run_at`、lease、misfire policy、独立 scheduler state。
6. Workflow Orchestration Depth：当前不支持复杂 DAG、并行/条件分支、Saga、复杂 Policy DSL、可视化 Designer。
7. Event Infrastructure：没有通用 MQ/Kafka/Event Bus；当前 Webhook 是受控 HTTP 入口。
8. Multi-Agent / Marketplace：尚未形成正式 Product Contract。

## 3. 优先级路线

| 优先级 | 后续阶段 | 产品主题 | 企业场景 | 进入条件 |
|---|---|---|---|---|
| P0 | Phase 2.1 | Enterprise Organization & Access Governance | 企业管理员需要管理组织、成员、角色和资源边界 | 已完成并正式关闭 |
| **P0** | **Phase 2.2 / 2.2-E** | **Retrieval Production Quality + Model Provider/Profile Foundation** | 企业需要稳定检索质量，并能够明确选择和追踪实际模型 | **当前正式实施** |
| P1 | Phase 2.3 | Model Provider Governance | 企业需要 Provider 路由、Fallback、模型白名单、成本/用量治理 | 明确成本口径、路由策略与 Provider Contract |
| P1 | Phase 2.4 | Durable Scheduler | 企业任务需要长期运行、故障恢复、misfire 与多实例语义 | 明确 scheduler lease / misfire / next-run Contract |
| P1 | Phase 2.5 | Advanced Workflow Orchestration | 企业流程需要并行、条件、重试分支、人工节点或补偿 | 明确 Workflow DSL 与执行语义 |
| P2 | Phase 2.6 | Enterprise Integration / Event Infrastructure | 企业系统需要稳定事件集成、异步解耦和高吞吐事件处理 | Webhook 无法满足真实吞吐/可靠性需求时立项 |
| P2 | Phase 2.7 | Multi-Agent Collaboration | 复杂任务需要多个专职 Agent 协同 | 明确业务场景、协作协议、权限与成本边界 |
| P2 | Phase 2.8 | Agent Asset / Marketplace | 企业需要 Agent 模板复用、发布、共享和生命周期管理 | 明确资产所有权、版本、审批和跨组织共享模型 |

## 4. 当前正式开发阶段：Phase 2.2

### 2.2-E 目标

建立可治理的 Model Provider / Model Profile 基础设施：

```text
Organization
   ↓
Model Provider
   ├── provider_type
   ├── provider_name
   ├── endpoint
   └── credential_ref
          ↓
      Model Profile
      ├── chat
      └── embedding + dimension
```

### 2.2-E 首阶段范围

- Provider / Profile 数据模型。
- Organization scope。
- Provider / Profile CRUD API。
- Owner/Admin 权限。
- Credential reference 安全边界。
- Default Profile 语义。
- Audit / Trace 基础身份。
- Migration 与 API Contract tests。

### 2.2-E 后续

- Runtime 根据 `model_profile_id` 解析 Provider。
- AgentVersion / Chat 使用 Profile identity。
- Evaluation runner 使用 Profile identity。
- Execution / Evaluation trace 固化 Provider/Profile/model/dimension。
- Provider/Profile 管理 UI 与 Browser E2E。

### 明确不直接纳入 2.2-E

- Reranker。
- 新 Hybrid Search 实现。
- Provider Fallback。
- Provider routing。
- 成本/用量治理。
- MQ/Kafka/Temporal。
- Multi-Agent orchestration。

这些能力仍属于后续独立 Product Contract。

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

对于 Retrieval Quality / Model Profile，额外必须回答：

11. 评测数据集如何版本化？
12. Recall / Precision / Citation 的计算定义是什么？
13. 最低质量门槛是什么？
14. Provider / model / dimension 变更如何进行回归比较？
15. Runtime / Evaluation 如何记录受治理 Profile identity？

## 6. 风险控制

- 不重新启用历史 `HISTORICAL_PHASE_*` 文档。
- 不直接把 MQ/Kafka、Temporal、复杂 DAG、Multi-Agent 等技术名词变成产品需求。
- 不修改已通过的 Runtime Reliability / Organization Governance 边界来“顺便支持”新能力。
- 新增数据库字段/表必须先设计 Migration，再实现依赖代码。
- 真实 Provider 的质量结论必须来自本地真实 Provider 验证，不得用 Mock 结果代替。
- 每个正式 Phase 完成后必须同步 Phase、Acceptance、Project Status、错误记录。
- 2.2-E 不等于完整 Phase 2.3；完整 Provider routing/Fallback/cost governance 必须独立立项与 Contract。

## 7. 当前执行结论

**Phase 2.2 正在继续。当前工作为 2.2-E Model Provider / Model Profile Governance Foundation；先完成模型身份治理基础设施，再完成 Runtime / Evaluation Profile Resolution，之后才评估 Phase 2.2 关闭。**
