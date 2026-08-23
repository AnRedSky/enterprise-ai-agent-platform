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
| Frontend | Vue 3 + API Types + Governance UI | 已验收当前范围 | 后续 Phase 按用户操作范围决定 |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收当前范围 | 随后续 Phase 范围进入独立 Gate |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 正式关闭 | 否，除回归 |
| **2.3** | **Model Provider Governance（路由/Fallback/成本/用量）** | **正式关闭** | **否，除回归** |
| **2.4** | **Durable Scheduler** | **已确认下一正式工作，Contract 设计中** | **是** |
| 2.5 | Advanced Workflow Orchestration | 候选路线 | 2.4 后按需求确认 |
| 2.6 | Enterprise Event Infrastructure | 候选路线 | 真实吞吐/可靠性需求出现时确认 |
| 2.7 | Multi-Agent Collaboration | 候选路线 | 业务场景确认后 |
| 2.8 | Agent Asset / Marketplace | 候选路线 | 产品资产模型确认后 |

## 3. Phase 2.3 实现矩阵

| 能力 | Contract | 当前实现 | 验证 |
|---|---|---|---|
| Routing strategy | explicit_profile / organization_default | routing resolver + Runtime | 2.3-E Passed |
| Fallback | transport failures + max attempts 2 | Runtime invocation + `FallbackPolicy` | 2.3-F Passed |
| Model whitelist | capability + provider allowlist + model type | routing resolver | 2.3-E Passed |
| Cost | usage units + pricing source/version | PostgreSQL `model_usage_records` + pricing calculator + usage API | 2.3-G Passed |
| Usage identity | organization/provider/profile/request/trace/outcome | Workflow Trace + durable usage record | 2.3-G Passed |

## 4. Phase 2.4 Contract 决策矩阵

| 能力 | 首版确认方案 | 灵活性边界 |
|---|---|---|
| 调度对象 | 已发布 Workflow 的 Scheduled Trigger | 不新增通用 Job 产品概念 |
| `next_run_at` | UTC 持久化 + IANA timezone | clock abstraction 可替换 |
| Lease | PostgreSQL 原子 lease / ownership | 后续可替换为专用协调基础设施 |
| 幂等 | `trigger_id + planned_slot` 持久化唯一键 | 数据库唯一约束为最终边界 |
| Misfire | `skip` / `fire_once` / 有上限 `catch_up` | 不支持无限追赶 |
| 状态 | `enabled` / `paused` / `disabled` | 恢复行为由 misfire policy 决定 |
| Trace | Scheduler decision 与 WorkflowExecution 关联 | 不泄露 Secret |
| 基础设施 | 首版不引入 MQ/Kafka/Temporal | 真实容量证据不足时不提前扩张 |

## 5. Phase 2.4 进入代码前 Gate

- `next_run_at` / timezone / clock 语义确认；
- Lease ownership、过期、抢占和重复执行边界确认；
- misfire、幂等和重复触发边界确认；
- 状态转换确认；
- Audit / Trace 关联字段确认；
- PostgreSQL Migration 与 Real API acceptance 场景确认。

Contract 未确认前，不创建 Scheduler Migration、Service、API 或 UI 代码。
