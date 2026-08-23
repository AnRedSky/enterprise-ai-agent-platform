# 产品需求与功能开发对比矩阵

> 基线：当前 `main`
> 目的：将产品能力目标、当前实现、验收证据、明确缺口、下一步决策放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有项目实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 当前核心能力

| 产品域 | 当前实现 | 验收状态 | 下一动作 |
|---|---|---|---|
| Runtime | Runtime + Session + Context + Model/Tool/Knowledge/Memory + governed provider invocation | 2.3-E 已验收 | 2.3-F fallback policy enforcement |
| Model Gateway | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 继续承载 governed provider invocation |
| Model Provider / Profile | Provider/Profile 数据模型、CRUD、Organization scope、Audit | 2.2-E 已验收 | Runtime governance |
| Provider Governance | routing/fallback/cost/usage Contract + routing API + Runtime invocation | 2.3-E 已验收；2.3-F 待验证 | Cost / Usage accounting |
| Observability | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 继续承载 provider/profile/usage identity |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已验收当前范围 | Provider fallback policy / usage governance |
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
| Fallback | transport failures + max attempts 2 | Runtime invocation + `FallbackPolicy` | 2.3-E Passed；2.3-F policy enforcement 待验证 |
| Model whitelist | capability + provider allowlist + model type | routing resolver | 2.3-E Passed |
| Cost | usage units + pricing source/version | Contract；尚未持久化/计费 | 2.3-G |
| Usage identity | organization/provider/profile/request/trace/outcome | Workflow Trace persistence | 2.3-E Passed |

## 4. 当前产品完成判定

- 2.3-A/B/C/D 已实现。
- 2.3-E Real API acceptance 已通过。
- 2.3-F 正在实现 Runtime fallback policy enforcement，尚未完成本地验证。
- 当前无新增 Frontend/Browser 用户链路，因此本阶段继续裁剪 UI/E2E 范围。

## 5. 当前正式任务

**2.3-F Fallback Policy Enforcement** 已提交 `dd037f8`。

该任务必须保证：

1. fallback 最大 attempts 不得超过 2；
2. `FallbackPolicy.enabled` 真正控制是否允许 fallback；
3. `eligible_reasons` 真正控制哪些 provider failure 可以触发下一候选；
4. Runtime 不得通过调用参数绕过 policy；
5. 继续保持 organization/profile/provider/trace identity 与 Secret boundary。

2.3-F Gate 全部通过后，下一任务为 **2.3-G Cost / Usage Accounting**。若需要数据库持久化，先 Migration。
