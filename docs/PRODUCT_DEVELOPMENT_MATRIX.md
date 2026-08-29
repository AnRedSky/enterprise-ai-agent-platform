# 产品需求与功能开发对比矩阵

> 基线：当前 `main`（2026-08-29）
> 目的：将产品能力目标、当前实现、验收证据、明确缺口、下一步决策放在同一张可追溯矩阵中。
> 规则：`已实现` 只表示当前代码/Phase 已有对应能力；`已验收` 必须有实际 Acceptance 证据；`待决策` 不得直接转化为开发任务。
> 长期未完成企业化能力不在本矩阵中展开为阶段任务，统一由 `docs/05-long-term/` 独立记录。

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
| Frontend | Vue 3 + API Types + Governance UI | 已验收历史范围 | Phase 2.8 无专用 UI |
| Browser E2E | Playwright Browser → Vue → Backend | 已验收历史范围 | 新增 UI 后再扩展 |
| Multi-Agent | Delegation Domain/API + lifecycle + Worker Runtime | **B6 Real Runtime 已验收** | Phase 2.8 文档收口；进入 2.9 Contract 评估 |

## 2. Phase 映射

| Phase | 主要产品能力 | 当前状态 | 是否继续 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已关闭 | 否，除回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 已关闭 | 否，除回归 |
| 2.3 | Model Provider Governance | 已关闭 | 否，除回归 |
| 2.4 | Durable Scheduler | 已完成主线收口 | 否，除回归 |
| 2.5 | Scheduler → Worker Execution Decoupling | 已关闭 | 否，除回归 |
| 2.6 | Durable Execution Checkpoint Foundation | 已关闭 | 否，除回归 |
| 2.7 | Advanced Workflow Orchestration | 主线生产实现完成，Backend / Migration / Tenant Safe Real API 有实际证据 | 仅必要发布验收 |
| **2.8** | **Multi-Agent Collaboration** | **Domain/API/Migration/Runtime Integration 已完成；B6 Real Gate 已通过** | **Phase 收口** |
| **2.9** | **Enterprise Integration / Event Infrastructure** | **候选，尚未冻结 Contract** | **先做现状盘点与 Contract 决策** |
| 2.10 | Agent Asset / Marketplace | 候选 | 明确资产所有权、版本、审批和跨组织共享后再立项 |

## 3. Phase 2.8 实现矩阵

| 能力 | Contract | 当前实现 | 验证 |
|---|---|---|---|
| Delegation identity | 已冻结 | 已实现 | Unit / API Contract |
| Tenant / version / permission guard | 已冻结 | 已实现 | Unit / Contract / Real API 范围 |
| Depth / active-count / timeout / model budget | 已冻结 | 已实现 | Unit / Contract / Runtime |
| Durable Entity / Repository / API | 已冻结 | 已实现 | Migration / API Contract |
| Lifecycle / fencing pure rules | 已冻结 | 已实现 | Targeted Unit |
| Atomic Worker Claim | 已冻结 | 已实现 | B6 Unit/Contract + Real Runtime |
| Worker Execution bridge | 已冻结 | 已实现 | B6 Real Runtime |
| Generation-fenced persistence | 已冻结 | 已实现 | B6 Runtime / fencing tests |
| Timeout / cancel runtime | 已冻结 | 已实现 | B4 Runtime / Real API evidence |
| Audit / Trace runtime closure | 已冻结 | 已实现 | B5 + B6 Runtime evidence |
| Multi-worker concurrency | 已冻结 | **已实现并验收** | B6 Real HTTP + PostgreSQL, 5 passed |

### B6 最新实际验收证据

```text
Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

Migration/head
0039_workflow_node_execution_tenant_trigger (head)

Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

B6 Gate 还包含 Windows 外部 Worker/Scheduler 隔离检查，用于避免本地后台消费者污染验收数据；Gate 不自动启动、停止或重启服务。

## 4. 当前技术一致性问题

本轮核查未发现仍足以阻塞 Phase 2.8 收口的新 Runtime 问题。此前 `AgentDelegationService` 与 `lifecycle.py` 重复维护 lifecycle 规则的问题属于 B1 前约束，目前历史错误记录应作为已修复事实保留，不应继续作为当前 blocker。

当前需要重点防止的是文档基线漂移：旧文档仍可能保留历史状态文字；当前长期能力缺口统一见 `docs/05-long-term/README.md` 及 LT-01～LT-10 独立记录。

## 5. Phase 2.8 收口门槛

Phase 2.8 当前已经满足本轮定义的 Backend Runtime 收口条件：合法 Claim、2+ Worker ownership、stale completion fencing、completed/cancel/timeout fencing、真实 target Agent execution、context isolation、parent Workflow semantics、Audit / Trace 关系以及真实 PostgreSQL 持久化均已有对应实现和验收证据。

Browser E2E 不属于当前 Phase 2.8 必选项，因为本 Phase 未增加专用 Delegation UI；不得为了满足形式上的“全 Gate”而重复创建 UI。

## 6. Phase 2.9 进入条件

进入 Phase 2.9 前必须完成：

1. 现有 Integration / Event Infrastructure 代码盘点；
2. 确认是否已有可复用的 Event / Webhook / Trigger / Audit / Trace / Outbox 等正式实现；
3. 明确真实产品场景与可靠性需求，而不是先选 Kafka / MQ；
4. 冻结 Contract 后再创建 Phase 2.9 正式文档与开发任务；
5. 遵循 Contract → Migration → Backend implementation → Unit/Integration → Real API Gate 的既定顺序。

长期任务索引：`docs/05-long-term/README.md`。
