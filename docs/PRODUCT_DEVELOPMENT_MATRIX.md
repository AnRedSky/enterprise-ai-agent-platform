# 产品需求与功能开发对比矩阵

> 基线：当前 `main`
> 目的：将产品能力目标、当前实现、验收证据、明确缺口、下一步决策放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 当前核心能力

| 产品域 | 当前实现 | 验收状态 | 下一动作 |
|---|---|---|---|
| Runtime | Runtime + Session + Context + Model/Tool/Memory/Knowledge + governed provider invocation | 2.3-F 已验收 | 2.3-G Cost / Usage Accounting 验证 |
| Model Gateway | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 继续承载 governed provider invocation |
| Model Provider / Profile | Provider/Profile 数据模型、CRUD、Organization scope、Audit | 2.2-E 已验收 | Runtime governance |
| Provider Governance | routing/fallback/cost/usage Contract + routing API + Runtime invocation + fallback policy enforcement + usage accounting implementation | 2.3-F 已验收；2.3-G 待验证 | 完成 2.3-G 后重新评估 Phase closeout |
| Observability | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 继续承载 provider/profile/usage identity |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已验收当前范围 | Provider usage/cost governance |
| Frontend | Vue 3 + API Types + Governance UI | 已验收当前范围 | 2.3 当前无新增 UI 范围 |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收当前范围 | 随后续 2.3 UI 范围裁剪 |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 正式关闭 | 否，除回归 |
| **2.3** | **Model Provider Governance（路由/Fallback/成本/用量）** | **进行中** | **是** |
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
| Cost | usage units + pricing source/version | PostgreSQL `model_usage_records` + pricing calculator + usage API | 2.3-G 待验证 |
| Usage identity | organization/provider/profile/request/trace/outcome | Workflow Trace + durable usage record | 2.3-E Passed；2.3-G 待验证 |

## 4. 当前产品完成判定

- 2.3-A/B/C/D 已实现。
- 2.3-E Real API acceptance 已通过。
- 2.3-F Fallback Policy Enforcement 已通过开发者本地 Gate。
- 2.3-G Cost / Usage Accounting 已提交第一版，尚未完成本地 acceptance。
- 当前无新增 Frontend/Browser 用户链路，因此本阶段继续裁剪 UI/E2E 范围。

## 5. 当前正式任务

**2.3-G Cost / Usage Accounting**。

必须保证：

1. 每个 governed provider attempt 都产生 durable usage record；
2. request / input token / output token units 与 provider outcome 可追溯；
3. pricing source/version 与实际 cost calculation 可追溯；
4. organization/tenant scope 不可越权查询；
5. Secret、endpoint、credential_ref 不进入 usage/audit/trace；
6. usage 与 `model.invocation` trace 在同一事务中保持一致；
7. 新增数据库结构必须先经过 Alembic migration，再进行业务验收。

2.3-G 全部 Gate 通过后，再决定是否关闭 Phase 2.3；不得提前切换到候选 Phase 2.4。
