# 企业级 AI Agent Platform 产品整体实现路线

> 基线：远端 `main`
> 评估日期：2026-08-29
> 目的：以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
> 规则：只有已进入正式 Phase 的范围才允许转化为开发任务；候选路线必须先完成 Contract 决策。
> 长期未完成能力的独立任务记录统一位于 `docs/05-long-term/`，不与当前 Phase 文档混合。

## 1. 产品目标

平台目标是逐步成为企业可实际运营的 AI 应用基础平台：企业身份与组织 → AI 资产治理 → Agent / Workflow / Knowledge → 安全执行与可靠性 → 真实业务集成 → 运营、成本、质量与审计 → 多 Agent / 高级编排。

## 2. 当前基线判断

已完成并保持稳定的核心能力包括 Auth / RBAC / Tenant / Organization、Agent / Version / Runtime / Session、Model Gateway、Tool Runtime、Memory、Observability / Audit / Trace、Knowledge / RAG、Workflow / Execution Governance / Reliability / Circuit Breaker、Manual / Scheduled / Webhook Trigger、Vue 管理与调试界面、Model Provider / Profile Governance、Provider routing / governed fallback、Durable usage / cost accounting、Durable Scheduler，以及 Phase 2.7 Advanced Workflow Orchestration 的 Conditional Branching、Multi-frontier、Durable Resume、Recovery / Replay、Worker fencing、Frontier terminalization 与 checkpoint lifecycle guard。

Phase 2.8 已进一步完成受治理的 Multi-Agent Delegation Runtime：Delegation Durable Entity、Atomic Claim、既有 Workflow Worker bridge、generation-fenced completion/failure、timeout/cancel/parent semantics、Audit/Trace closure，以及多 Worker Durable Frontier acceptance。

## 3. 当前正式阶段

**Phase 2.8 Multi-Agent Collaboration Runtime Integration 已完成；B6 Real Gate 已通过。当前工作进入 Phase 2.8 文档收口与 Phase 2.9 Contract 前置评估。**

## 4. 当前 Phase 路线

| Phase | 产品主题 | 当前状态 | 下一动作 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已正式关闭 | 仅回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 已正式关闭 | 仅回归 |
| 2.3 | Model Provider Governance | 已正式关闭 | 仅回归 |
| 2.4 | Durable Scheduler | 已完成主线收口 | 仅回归 |
| 2.5 | Scheduler → Worker Execution Decoupling | 已正式关闭 | 仅回归 |
| 2.6 | Durable Execution Checkpoint Foundation | 已正式关闭 | 仅回归 |
| 2.7 | Advanced Workflow Orchestration | 主线生产实现完成 | 仅必要发布验收 |
| **2.8** | **Multi-Agent Collaboration** | **Runtime Integration 完成；B6 Real Gate 已通过** | **文档/Acceptance 收口** |
| **2.9** | **Enterprise Integration / Event Infrastructure** | **候选，尚未冻结 Contract** | **先做 Integration/Event 现状盘点与 Contract 决策** |
| 2.10 | Agent Asset / Marketplace | 候选 | 明确资产所有权、版本、审批和跨组织共享后再立项 |

## 5. 长期未完成能力

以下能力已经确认属于企业化长期缺口，但尚未进入正式 Phase。每项均独立维护长期任务文档：

| LT | 产品能力 | 状态 | 独立记录 |
|---|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | 待立项 | `docs/05-long-term/LT-01-ENTERPRISE-INTEGRATION-EVENT-INFRASTRUCTURE.md` |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 | `docs/05-long-term/LT-02-ENTERPRISE-IAM-SSO-IDENTITY.md` |
| LT-03 | Enterprise Operations Console | 待立项 | `docs/05-long-term/LT-03-ENTERPRISE-OPERATIONS-CONSOLE.md` |
| LT-04 | API / Developer Platform | 待立项 | `docs/05-long-term/LT-04-API-DEVELOPER-PLATFORM.md` |
| LT-05 | Observability / SRE | 待立项 | `docs/05-long-term/LT-05-OBSERVABILITY-SRE.md` |
| LT-06 | Security / Secrets / Policy | 待立项 | `docs/05-long-term/LT-06-SECURITY-SECRETS-POLICY.md` |
| LT-07 | Agent Evaluation / Quality | 待立项 | `docs/05-long-term/LT-07-AGENT-EVALUATION-QUALITY.md` |
| LT-08 | Cost / Quota / Billing | 待立项 | `docs/05-long-term/LT-08-COST-QUOTA-BILLING.md` |
| LT-09 | Agent Asset / Marketplace | 候选 | `docs/05-long-term/LT-09-AGENT-ASSET-MARKETPLACE.md` |
| LT-10 | Production Deployment / HA / Operations | 待立项 | `docs/05-long-term/LT-10-PRODUCTION-DEPLOYMENT-HA-OPERATIONS.md` |

LT 文档是 backlog/长期设计记录，不等价于当前开发任务。只有正式立项并冻结 Contract 后，才转化为新的 `PHASE_x_y.md`。

## 6. Phase 2.8 当前开发边界

首版只支持一次 Workflow Execution 内受治理的 Agent Delegation：绑定 tenant、source/target Agent version、稳定 delegation identity；显式传递 input/context/tool refs；限制 depth、active count、timeout、model budget；复用既有 RBAC / Model Governance / Durable Execution；Worker completion 必须 generation fenced；不引入 MQ/Kafka、Marketplace、跨 tenant 调用、无限 spawning 或第二套 Retry / Recovery 状态机。

详细 Contract：`docs/02-phases/PHASE_2_8_A_CONTRACT.md`。

## 7. Phase 2.8 开发顺序与完成状态

```text
Contract 冻结
    ↓
Domain + API + Migration                    ✅
B1 Atomic Delegation Claim                  ✅
B2 Existing Worker Execution bridge         ✅
B3 generation-fenced completion/failure     ✅
B4 timeout / cancel / parent semantics      ✅
B5 Audit / Trace closure                   ✅
B6 multi-worker Durable Frontier runtime    ✅
    ↓
Phase 2.8 Runtime Integration               ✅ 收口
```

## 8. B6 实际验收证据

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

实际结果：

```text
[1/4] Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

[2/4] Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

[3/4] Migration/head verification
0039_workflow_node_execution_tenant_trigger (head)

[4/4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

B6 Gate 同时包含 Windows 外部 Worker/Scheduler 隔离检查。Gate 不启动、停止或重启本地服务，只检查前置环境并执行正式验收链路。

## 9. B6 工程问题闭环

B6 开发期间发现并修复了 PostgreSQL Claim contention 与固定轮次时序误判、旧 B2 Real API 绕过正式 Frontier dispatch、Worker shutdown AsyncEngine cancellation、外部 Worker/Scheduler 环境污染以及 Windows PowerShell 进程检测正则解析等问题。对应错误分析已进入 `docs/04-errors/`；最新状态不再存在已知 B6 Runtime blocker。

## 10. Phase 2.9 进入前置条件

Phase 2.9 不应直接开始功能编码。必须先完成：

1. 盘点现有 Event、Webhook、Trigger、Audit、Trace、Outbox 等实现；
2. 检查是否已有正式 Integration / Event Infrastructure 领域模块，避免复制第二套 Service / Repository / Runtime / Provider；
3. 根据真实企业业务场景确定可靠性、交付语义、幂等、重试、顺序性、隔离和可观测边界；
4. 只有 Contract 冻结后，才创建正式 Phase 2.9 文档和开发任务；
5. 涉及数据库结构时必须 Migration-first，并通过真实 `alembic upgrade head` 验证；
6. 按既定顺序进入 Backend Domain / API → Unit / Integration / Contract → Real API → Frontend / E2E（如范围需要）→ Acceptance。

**Kafka、MQ、Outbox、Event Bus 等技术选型不得先于业务 Contract 决策。**

## 11. 工程纪律

所有实际完成度以代码、Phase、Acceptance 与本地测试证据为准。未执行的测试不得标记 Passed；Phase 完成、延期、阻塞或范围变更必须同步更新 Phase / Acceptance / Project Status / Error 文档；所有开发、修复与文档变更直接基于并提交 `main`，不创建功能分支。
