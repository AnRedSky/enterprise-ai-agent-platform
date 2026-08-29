# 企业级 AI Agent Platform 产品能力基线

> 基线：远端 `main`，评估日期：2026-08-29
> 文档性质：产品能力与工程实现基线；实际完成度必须以仓库代码、Phase 文档及 Acceptance 证据为准。

## 1. 产品定位

Enterprise AI Agent Platform 面向企业应用场景，当前采用 FastAPI + Vue 3 + PostgreSQL + Redis 单体边界，通过版本化 API 提供 Agent、Runtime、Model、Tool、Knowledge、Memory、Workflow、Trigger、Observability 与 Governance 能力。

长期目标包括高可用、高并发、可维护、可扩展、多 Agent 协作、企业级安全、可观测和可治理。

## 2. 当前产品架构

```text
User / Enterprise App
        ↓
FastAPI API
        ↓
Auth / RBAC / Tenant / Organization Governance
        ↓
Agent / Workflow Services
        ↓
Agent Runtime / Workflow Runtime
 ├── Context / Session / Message
 ├── Model Gateway / Provider Governance
 ├── Tool Runtime
 ├── Knowledge / RAG
 ├── Memory
 ├── Trigger / Durable Scheduler / Webhook
 ├── Durable Frontier / Resume / Recovery
 └── Observability / Audit / Trace
        ↓
PostgreSQL / Redis

Vue 3 Management / Debug UI
        ↓
Versioned Backend API Contract
```

## 3. 产品能力全景

| 能力域 | 当前工程状态 | 当前验收结论 | 下一动作 |
|---|---|---|---|
| Identity / Auth / Organization | 已实现 | 2.1 已关闭 | 仅回归 |
| Agent / Agent Version | 已实现 | 当前范围已验收 | 继续承载 Agent Governance |
| Agent Runtime | 已实现 | 历史 Reliability Gate 已验收 | 保持可靠性基线 |
| Model Gateway / Provider Governance | 已实现 | 2.2 / 2.3 已关闭 | 继续作为 Worker model governance |
| Tool Runtime | 已实现 | 当前范围已验收 | 保持安全边界 |
| Memory / Knowledge / RAG | 已实现 | 当前范围已验收 | 后续按需求演进 |
| Workflow / Execution | 已实现 | 2.7 主线生产实现完成 | 继续作为 Delegation Runtime 基础 |
| Durable Scheduler | 已实现 | 已完成主线收口 | 仅回归 |
| Durable Resume / Recovery | 已实现 | 2.7 主线已收口并有实际 Backend / Real API 证据 | 保持回归 |
| Observability / Audit / Trace | 已实现 | 已验收当前范围 | 承载 Delegation trace |
| Frontend / Browser E2E | 已实现 | 历史范围已验收 | 新 UI 再扩展 |
| Multi-Agent Collaboration | **Delegation Domain/API/Migration/Worker Runtime 已实现** | **B6 Real Runtime 已验收** | **Phase 2.8 文档收口；进入 Phase 2.9 Contract 评估** |

## 4. 当前核心闭环

### Workflow

```text
Workflow Definition
 → Version / Publish
 → Trigger
 → Execution
 → Frontier / Worker
 → Checkpoint / Resume / Recovery
 → Audit / Trace
```

### Multi-Agent Delegation

```text
Orchestrator Execution
 → Delegation(pending)
 → Atomic Claim
 → Worker Execution / Durable Frontier
 → Agent Runtime
 → generation-fenced completion / failure
 → timeout / cancel
 → Audit / Trace
```

该闭环当前已经获得 B6 真实 HTTP + PostgreSQL + 多 Worker Durable Frontier Runtime 验收证据。

## 5. 当前正式路线

1. Phase 2.1 — Organization & Access Governance：已关闭。
2. Phase 2.2 — Retrieval Production Quality + Model Provider/Profile：已关闭。
3. Phase 2.3 — Model Provider Governance：已关闭。
4. Phase 2.4 — Durable Scheduler：已完成主线收口。
5. Phase 2.5 — Scheduler → Worker Execution Decoupling：已关闭。
6. Phase 2.6 — Durable Execution Checkpoint Foundation：已关闭。
7. Phase 2.7 — Advanced Workflow Orchestration：主线生产实现完成，Backend / Migration / Tenant Safe Real API 已有实际证据。
8. **Phase 2.8 — Multi-Agent Collaboration：Runtime Integration 已完成，B6 Real Gate 已通过，当前进入收口。**
9. **Phase 2.9 — Enterprise Integration / Event Infrastructure：候选，尚未冻结 Contract。**
10. Phase 2.10 — Agent Asset / Marketplace：候选。

## 6. Phase 2.8 当前边界与完成度

首版只支持一次 Workflow Execution 内受治理的 Agent Delegation。必须绑定 tenant、source/target Agent version、稳定 delegation identity，显式声明 input/context/tool refs，限制 depth / active count / timeout / model budget，并复用既有 RBAC、Model Governance、Workflow Worker / lease / fencing / Retry / Recovery。

不提前引入 MQ/Kafka、Marketplace、跨 tenant 调用、无限 spawning 或第二套可靠性状态机。

Phase 2.8 当前子任务：

```text
B1 Atomic Delegation Claim                   ✅
B2 Existing Worker Execution bridge          ✅
B3 generation-fenced completion / failure    ✅
B4 timeout / cancel / parent semantics       ✅
B5 Audit / Trace closure                    ✅
B6 multi-worker Durable Frontier runtime     ✅
```

## 7. B6 实际验收基线

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

B6 Gate 同时执行 Windows 外部 Worker/Scheduler 隔离检查，以避免本地后台消费者污染测试数据。Gate 不自动启动、停止或重启任何服务。

## 8. 当前工程一致性结论

此前 `lifecycle.py` 与 `AgentDelegationService` 重复维护生命周期规则的问题已属于历史工程问题，不应继续作为当前 Phase 2.8 blocker。当前状态、验收结果和后续路线以最新 `PROJECT_STATUS.md`、B6 实际验收证据以及本文件为准。

当前没有证据表明 Phase 2.8 仍存在已知 Runtime 阻塞。后续除非出现新的实际回归，不再重复修改已通过的 Claim、Worker dispatch、timeout/cancel 或 shutdown cleanup 路径。

## 9. Phase 2.9 进入原则

Phase 2.9 尚未进入正式开发。进入前必须完成现有 Integration / Event Infrastructure 盘点，包括 Event、Webhook、Trigger、Audit、Trace、Outbox 等现有实现；只有确定真实产品需求、可靠性边界和 Contract 后，才能建立正式 Phase 文档与开发任务。

新增能力必须继续遵循：

```text
Contract
  ↓
Migration（如涉及数据结构）
  ↓
Backend Domain / API
  ↓
Unit / Integration / Contract tests
  ↓
Real API
  ↓
Frontend / E2E（如范围需要）
  ↓
Acceptance + Project Status
```

并严格遵循 `docs/01-governance/DEVELOPMENT.md` 的领域模块化、唯一业务规则入口、Provider 唯一实现、测试 Gate 隔离以及直接提交 `main` 的规则。

## 10. 验收纪律

未实际执行的测试不得标记 Passed。Real API 必须证明真实 HTTP + PostgreSQL 持久化；Runtime 生命周期必须实际验证 Worker / Scheduler；所有 Phase 完成、延期、阻塞或范围变更必须同步更新 Phase、Acceptance、Project Status 与 Error 记录。
