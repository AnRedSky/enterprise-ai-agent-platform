# 产品需求与功能开发对比矩阵

> 基线：当前 `main`（2026-08-28）
> 目的：将产品能力目标、当前实现、验收证据、明确缺口、下一步决策放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。

## 1. 当前核心能力

| 产品域 | 当前实现 | 验收状态 | 下一动作 |
|---|---|---|---|
| Runtime | Agent Runtime + Workflow Runtime + Context/Session/Model/Tool/Memory/Knowledge | 已验收当前历史范围 | 后续 Phase 只扩展明确 Contract |
| Model Gateway | Mock/OpenAI-compatible、普通/流式 Contract | 已覆盖当前范围 | 承载 governed provider invocation |
| Model Provider / Profile | Provider/Profile 数据模型、CRUD、Organization scope、Audit | 2.2-E 已验收 | 保持治理入口唯一 |
| Provider Governance | routing/fallback/policy/cost/usage + durable accounting | 2.3 已正式关闭 | 仅回归 |
| Observability | Execution/Event/Trace/Audit + UI | 已验收当前范围 | 承载 Delegation trace |
| Governance | Tenant/RBAC/Audit/Trace/Reliability | 已验收当前范围 | 继续作为跨 Agent 边界 |
| Workflow | Workflow / Execution / Retry / Recovery / Frontier | 2.7 主线完成 | 作为 Delegation Worker 基础 |
| Scheduler | Durable Scheduler / lease / misfire / trigger | 已完成主线收口 | 仅回归 |
| Frontend | Vue 3 + API Types + Governance UI | 已验收历史范围 | Phase 2.8 UI 暂不扩展 |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收历史范围 | 新增 UI 后再扩展 |
| Multi-Agent | Delegation Domain/API + lifecycle pure rules | Runtime 未完成 | B1-B5 |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 已关闭 | 否，除回归 |
| 2.3 | Model Provider Governance | 已关闭 | 否，除回归 |
| 2.4 | Durable Scheduler | 已完成主线收口 | 否，除回归 |
| 2.5 | Scheduler → Worker Execution Decoupling | 已关闭 | 否，除回归 |
| 2.6 | Durable Execution Checkpoint Foundation | 已关闭 | 否，除回归 |
| 2.7 | Advanced Workflow Orchestration | 主线生产实现完成，验收收口 | 是，完成必要发布验收 |
| **2.8** | **Multi-Agent Collaboration** | **Contract / Domain / API / Migration 已完成，Runtime Integration 进行中** | **是** |
| 2.9 | Enterprise Integration / Event Infrastructure | 候选 | 2.8 后评估 |
| 2.10 | Agent Asset / Marketplace | 候选 | 2.8 后评估 |

## 3. Phase 2.8 实现矩阵

| 能力 | Contract | 当前实现 | 验证 |
|---|---|---|---|
| Delegation identity | 已冻结 | 已实现 | Unit / API contract 已存在 |
| Tenant / version / permission guard | 已冻结 | 已实现 | Domain tests 已存在 |
| Depth / active-count / timeout / model budget | 已冻结 | 已实现 | Domain tests 已存在 |
| Durable Entity / Repository / API | 已冻结 | 已实现 | Migration 0038 + API contract |
| Lifecycle / fencing pure rules | 已冻结 | 已实现 | `test_agent_delegation_lifecycle.py`，待 `37061ab` 后本地执行 |
| Atomic Worker Claim | 已冻结 | **未实现** | B1 |
| Worker Execution bridge | 已冻结 | **未实现** | B2 |
| Generation-fenced persistence | 已冻结 | **未实现** | B3 |
| Timeout / cancel runtime | 已冻结 | **未实现** | B4 |
| Audit / Trace runtime closure | 已冻结 | **未实现** | B5 |
| Multi-worker concurrency | 已冻结 | **未实现** | Real API acceptance |

## 4. 当前技术一致性问题

`lifecycle.py` 已定义正式 lifecycle 规则，但 `AgentDelegationService` 仍保留重复的 `TERMINAL_STATES` / `TRANSITIONS`。当前内容一致但属于重复业务规则入口，已记录到 `docs/04-errors/`；B1 前必须收敛到唯一入口。

## 5. Phase 2.8 验收门槛

必须证明：合法 Claim、2+ Worker 并发 ownership、stale completion fencing、completed/cancel/timeout fencing、真实 target Agent execution、context isolation、parent Workflow semantics、Audit / Trace 双向反查，以及真实 PostgreSQL 状态一致性。

Browser E2E 仅在实际增加 Delegation UI 后加入；不得以 Browser Gate 替代 Backend Runtime acceptance。
