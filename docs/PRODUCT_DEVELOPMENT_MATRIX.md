# 产品需求与功能开发对比矩阵

> 基线：当前 `main`
> 目的：将产品能力目标、当前实现、验收证据、明确缺口、下一步决策放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 当前核心能力

| 产品域 | 当前实现 | 验收状态 | 下一动作 |
|---|---|---|---|
| Runtime | Runtime + Session + Context + Model/Tool/Memory/Knowledge + governed provider invocation | Phase 2.3 已关闭 | 进入后续 Phase 时保持回归 |
| Model Gateway | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 继续承载 governed provider invocation |
| Model Provider / Profile | Provider/Profile 数据模型、CRUD、Organization scope、Audit | 2.2-E 已验收 | Provider Governance 已完成 |
| Provider Governance | routing/fallback/policy/cost/usage + durable accounting | 2.3-A~G 全部验收 | Phase 2.3 关闭 |
| Observability | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 继续承载 provider/profile/usage identity |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已验收当前范围 | 后续阶段复用治理边界 |
| Frontend | Vue 3 + API Types + Governance UI | 已验收当前范围 | Phase 2.3 无新增 UI 范围 |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收当前范围 | 随后续 Phase 范围进入独立 Gate |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 正式关闭 | 否，除回归 |
| **2.3** | **Model Provider Governance（路由/Fallback/成本/用量）** | **正式关闭** | **否，除回归** |
| 2.4 | Durable Scheduler | 候选路线 | 需求确认后 |
| 2.5 | Advanced Workflow Orchestration | 候选路线 | 需求确认后 |
| 2.6 | Enterprise Event Infrastructure | 候选路线 | 需求确认后 |
| 2.7 | Multi-Agent Collaboration | 候选路线 | 需求确认后 |
| 2.8 | Agent Asset / Marketplace | 候选路线 | 需求确认后 |

## 3. Phase 2.3 实现矩阵

| 能力 | Contract | 当前实现 | 验证 |
|---|---|---|---|
| Routing strategy | explicit_profile / organization_default | routing resolver + Runtime | 2.3-E Passed |
| Fallback | transport failures + max attempts 2 | Runtime invocation + `FallbackPolicy` | 2.3-F Passed |
| Model whitelist | capability + provider allowlist + model type | routing resolver | 2.3-E Passed |
| Cost | usage units + pricing source/version | PostgreSQL `model_usage_records` + pricing calculator + usage API | 2.3-G Passed |
| Usage identity | organization/provider/profile/request/trace/outcome | Workflow Trace + durable usage record | 2.3-G Passed |

## 4. Phase 2.3 关闭判定

- 2.3-A/B/C/D 已实现并验收。
- 2.3-E Real API acceptance 已通过。
- 2.3-F Fallback Policy Enforcement 已通过开发者本地 Gate。
- 2.3-G Cost / Usage Accounting 已通过 targeted、Backend regression、Migration 与 Tenant Safe Real API Gate。
- 当前无新增 Frontend/Browser 用户链路，因此 Phase 2.3 不新增 UI/E2E 范围。

## 5. 下一正式决策

候选 Phase 2.4 为 Durable Scheduler，但目前仍属于候选路线。进入正式开发前必须确认：`next_run_at`、scheduler lease、misfire policy、幂等与重复触发、状态转换、审计/trace 以及 Real API acceptance Contract。确认前不得直接创建 Scheduler 业务代码或 Migration。
