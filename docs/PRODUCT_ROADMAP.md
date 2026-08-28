# 企业级 AI Agent Platform 产品整体实现路线

> 基线：远端 `main`
> 评估日期：2026-08-29
> 目的：以真实企业产品场景为依据，对已确认能力缺口进行优先级排序，并形成后续阶段路线。
> 规则：只有已进入正式 Phase 的范围才允许转化为开发任务；候选路线必须先完成 Contract 决策。

## 1. 产品目标

平台目标是逐步成为企业可实际运营的 AI 应用基础平台：企业身份与组织 → AI 资产治理 → Agent / Workflow / Knowledge → 安全执行与可靠性 → 真实业务集成 → 运营、成本、质量与审计 → 多 Agent / 高级编排。

## 2. 当前基线判断

已完成并保持稳定的核心能力包括 Auth / RBAC / Tenant / Organization、Agent / Version / Runtime / Session、Model Gateway、Tool Runtime、Memory、Observability / Audit / Trace、Knowledge / RAG、Workflow / Execution Governance / Reliability / Circuit Breaker、Manual / Scheduled / Webhook Trigger、Vue 管理与调试界面、Model Provider / Profile Governance、Provider routing / governed fallback、Durable usage / cost accounting、Durable Scheduler，以及 Phase 2.7 Advanced Workflow Orchestration 的 Conditional Branching、Multi-frontier、Durable Resume、Recovery / Replay、Worker fencing、Frontier terminalization 与 checkpoint lifecycle guard。

## 3. 当前正式阶段

**Phase 2.7 主线生产实现已完成；当前主线进入 Phase 2.8 Multi-Agent Collaboration Runtime Integration，B1/B2/B3 已通过开发者本地实际验收，当前正在实现 B4。**

## 4. 优先级路线

| Phase | 产品主题 | 当前状态 | 下一动作 |
|---|---|---|---|
| 2.1 | Enterprise Organization & Access Governance | 已正式关闭 | 仅回归 |
| 2.2 | Retrieval Production Quality + Model Provider/Profile Foundation | 已正式关闭 | 仅回归 |
| 2.3 | Model Provider Governance | 已正式关闭 | 仅回归 |
| 2.4 | Durable Scheduler | 已完成主线收口 | 仅回归 |
| 2.5 | Scheduler → Worker Execution Decoupling | 已正式关闭 | 仅回归 |
| 2.6 | Durable Execution Checkpoint Foundation | 已正式关闭 | 仅回归 |
| 2.7 | Advanced Workflow Orchestration | 主线生产实现完成，验收收口 | 完成必要 Frontend / Browser 验收 |
| **2.8** | **Multi-Agent Collaboration** | **B1/B2/B3 已完成，本轮进入 B4** | **B4 → B5 → 多 Worker + PostgreSQL + Runtime acceptance** |
| 2.9 | Enterprise Integration / Event Infrastructure | 候选 | 2.8 后按真实吞吐/可靠性需求评估 |
| 2.10 | Agent Asset / Marketplace | 候选 | 明确资产所有权、版本、审批和跨组织共享后再立项 |

## 5. Phase 2.8 当前开发边界

首版只支持一次 Workflow Execution 内受治理的 Agent Delegation：绑定 tenant、source/target Agent version、稳定 delegation identity；显式传递 input/context/tool refs；限制 depth、active count、timeout、model budget；复用既有 RBAC / Model Governance / Durable Execution；Worker completion 必须 generation fenced；不引入 MQ/Kafka、Marketplace、跨 tenant 调用、无限 spawning 或第二套 Retry / Recovery 状态机。

详细 Contract：`docs/02-phases/PHASE_2_8_A_CONTRACT.md`。

## 6. Phase 2.8 开发顺序

```text
Contract 冻结
    ↓
Domain + API + Migration              ✅
B1 Atomic Delegation Claim            ✅
B2 Existing Worker Execution bridge   ✅
B3 generation-fenced completion       ✅
B4 timeout / cancel / parent semantics ← 当前
B5 Audit / Trace closure
    ↓
Real API + PostgreSQL + multi-worker acceptance
    ↓
Backend Regression
    ↓
Frontend / Browser E2E（如范围需要）
```

## 7. B4 交付定义

B4 必须证明：

1. Delegation timeout 与既有 Workflow Runtime timeout 取有效最短边界；
2. timeout 后子 Worker Execution 使用既有 Execution lifecycle 结束，不继续占用 Worker lease；
3. Delegation 独立收敛为 `timed_out`；
4. cancel 后 Delegation 为 `cancelled`，重复 cancel fail-closed；
5. timeout / cancel 不直接修改父 Workflow Execution terminal 状态；
6. timeout / cancel 后迟到 Worker completion/failure 被 generation fencing 拒绝；
7. 不引入新的 Retry / Recovery 状态机。

## 8. 工程纪律

所有实际完成度以代码、Phase、Acceptance 与本地测试证据为准。未执行的测试不得标记 Passed；新增 Migration 必须实际 `alembic upgrade head`；Phase 完成、延期、阻塞或范围变更必须同步更新 Phase / Acceptance / Project Status / Error 文档。
