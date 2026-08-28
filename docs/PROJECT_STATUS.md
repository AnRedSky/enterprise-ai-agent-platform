# 项目状态

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 最新 main：`f080ff53d1f5b5f5352ad36fc0be1d8e6d08e9e7` — `docs(status): reconcile phase 2.7 closure and delegation runtime plan`
- 上一代码基线：`37061abb99fefbf753c088f6644f24d289814c39` — `feat(phase-2.8): establish delegation lifecycle fencing contract`
- 本轮核查时间：2026-08-28

远端 `main` 当前没有新的生产代码变化；最新提交是对 Phase 2.7 / Phase 2.8 状态与运行时计划的文档收口。因此本轮重点是核对“文档声称”与“当前代码实际状态”是否一致，并修正文档漂移。

## 2. Phase 2.7 Advanced Workflow Orchestration

### 生产实现

Phase 2.7 主线生产实现已完成。当前已确认的能力包括 Durable Frontier claim / lease / fencing、checkpoint durable boundary、terminalization、retry exhaustion、Recovery / Replay、stale Worker fencing 与 completion fact uniqueness。

### 开发者实际验证证据

开发者已反馈上一代码基线 `b5e3c44484f9ffa231fb1f368cfc14afe0d99dea` 的真实结果：

```text
uv run pytest -q
824 passed, 3 skipped, 42 deselected in 34.22s

Tenant Safe Real API Gate
41 passed in 81.83s
[PASS] Tenant-safe Real API gate completed.

uv run alembic upgrade head
uv run alembic current
0039_workflow_node_execution_tenant_trigger (head)
```

这些结果可以作为 Phase 2.7 已完成主线实现的实际证据，但不能用于证明 `37061ab` 之后新增的 Phase 2.8 lifecycle 代码已经通过本地测试。

### 当前验收状态

`docs/03-acceptance/PHASE_2_7_ACCEPTANCE.md` 已同步为：生产主线代码完成；Backend Unit / Regression、Migration、Real API 的实际证据按开发者已反馈结果记录；Frontend / Browser E2E 若尚未重新执行则保持未验收状态。

Phase 2.7 不再是当前开发 blocker，后续只允许继续做明确未完成的验收或回归，不得重新打开已解决的 Resume checkpoint Contract 问题。

## 3. Phase 2.8 Multi-Agent Collaboration

### 3.1 Contract / Domain / API

Phase 2.8-A Contract 已冻结。当前已经实现：

- `AgentDelegation` Durable Entity；
- `AgentDelegationRepository`；
- `AgentDelegationService`；
- stable delegation identity / 幂等；
- tenant / source execution / source Agent version / target Agent version lineage；
- depth / active-count / timeout / model budget；
- create / list / get / cancel API；
- Audit / Trace 基础事件；
- active budget creation 的父 Execution 行锁序列化；
- `0038_agent_delegations` Migration。

当前数据库 head 为 `0039_workflow_node_execution_tenant_trigger`，其上游为 `0038_agent_delegations`，因此 Phase 2.8 当前没有新的 Migration 缺口。

### 3.2 Lifecycle / Fencing

`37061ab` 新增 `backend/app/services/agent_delegation/lifecycle.py`，集中定义：

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation
timeout → now >= timeout_at
```

Unit 测试 `backend/tests/unit/test_agent_delegation_lifecycle.py` 已存在并覆盖合法/非法状态转换、终态封闭、stale generation、缺失 owner 与 timeout 边界；但截至本次核查，没有开发者在 `37061ab` 之后提供新的本地执行结果，因此不得记录为 PASS。

### 3.3 深度代码核查发现

发现一项需要在进入 B1 前修正的代码一致性问题：

- `backend/app/services/agent_delegation/lifecycle.py` 已成为声明的生命周期唯一规则入口；
- 但 `backend/app/services/agent_delegation/service.py` 仍保留独立的 `TERMINAL_STATES` / `TRANSITIONS` 常量，并在 `cancel()` 中直接使用该副本；
- 两套当前内容一致，因此暂未形成行为差异，但违反“同一业务规则只能保留一个正式计算/校验入口”的开发准则，未来容易产生 Contract 漂移。

本问题已按开发准则记录到 `docs/04-errors/`，在 B1 Atomic Claim 开发前应删除 Service 内重复状态规则并统一调用 lifecycle 正式入口。

## 4. 当前真实缺口：Phase 2.8 Runtime Integration

当前 Delegation 是“可治理的持久化任务实体”，但还不是“可被现有 Worker 实际执行的闭环”。

```text
POST create
    ↓
pending Delegation
    ↓
[B1] Atomic Claim + worker_execution_id       ← 当前第一缺口
    ↓
[B2] Existing Workflow Worker Execution bridge
    ↓
Agent Runtime
    ↓
[B3] generation-fenced completion / failure
    ↓
[B4] timeout / cancel + parent semantics
    ↓
[B5] Audit / Trace closure
    ↓
Real API + multi-worker acceptance
```

### B1 — Atomic Delegation Claim

必须实现：

1. 仅 `pending` Delegation 可 Claim；
2. PostgreSQL 条件更新或行锁形成唯一 ownership boundary；
3. Claim 生成唯一 `worker_execution_id`；
4. 2+ Worker 并发竞争只能一个 generation 成为 owner；
5. timeout / cancelled / terminal Delegation fail-closed；
6. 不新增独立 Worker lease / Retry / Recovery 状态机。

### B2 — Workflow Worker Execution Bridge

复用现有 Workflow Worker / Execution / lease / fencing 能力，将 target Agent version、model profile、`input_data`、`selected_context_refs`、`allowed_tools` 与 delegation trace identity 显式装配到 Worker execution。

不得复制父 Execution 全量 checkpoint、memory 或 credential。

### B3/B4 — Completion / Failure / Timeout / Cancel

所有写回必须通过统一 lifecycle rule，并在事务内重新确认 `worker_execution_id`。stale Worker、已取消 Delegation、已超时 Delegation 均必须 fail-closed。Delegation 自身失败不直接终止父 Execution，由既有 Workflow Retry / Recovery Contract 决定父流程行为。

### B5 — Audit / Trace

形成：

```text
source Workflow Execution
  └── Delegation
        └── Worker Execution / Trace
```

必须支持父子反查，并禁止写入 Secret / credential 原文。

## 5. 当前验收矩阵

| 能力 | 当前状态 | 证据 / 说明 |
|---|---|---|
| Phase 2.7 生产主线 | ✅ 完成 | 代码已收口；历史本地 Regression / Real API 有实际结果 |
| Phase 2.7 最终 Acceptance | 🟡 收口中 | Frontend / Browser 等未重新执行部分保持未验收 |
| Phase 2.8 Contract | ✅ 冻结 | `PHASE_2_8_A_CONTRACT.md` |
| Delegation Domain / API | ✅ 已实现 | Entity / Repository / Service / API / Migration |
| Delegation lifecycle pure rules | 🟡 已实现待本地验证 | `37061ab` 新增 Unit 尚无新执行结果 |
| Service duplicate lifecycle rules | 🔴 待修正 | 与 lifecycle 正式入口重复，已记录错误 |
| Atomic Worker Claim | ⏳ 未实现 | 当前第一开发任务 |
| Worker Execution bridge | ⏳ 未实现 | B2 |
| Generation-fenced persistence | ⏳ 未实现 | B3 |
| Timeout / cancel runtime | ⏳ 未实现 | B3/B4 |
| Audit / Trace runtime closure | ⏳ 未实现 | B5 |
| Multi-worker concurrency acceptance | ⏳ 未实现 | B1-B5 完成后 |

## 6. 下一步唯一开发顺序

```text
1. 同步远端 main
2. 修正 Service 重复 lifecycle 规则并通过 targeted Unit
3. Phase 2.8-B1 Atomic Delegation Claim
4. B1 Unit + PostgreSQL Integration
5. B2 Existing Worker Execution bridge
6. B3 generation-fenced completion / failure
7. B4 timeout / cancel / parent semantics
8. B5 Audit / Trace closure
9. Phase 2.8 Real API Gate
10. 2+ Worker 并发 acceptance
11. Backend regression + migration verification
12. 如范围需要再进入 Frontend / Browser E2E
13. 同一原子提交同步 Phase / Acceptance / Status / Error 文档
```

## 7. 本地验证规则

所有测试结果必须以开发者本地实际执行为准。当前不能将 `37061ab` 新增 lifecycle Unit 标记为 PASS。

### Lifecycle targeted Unit

```powershell
cd backend
uv run pytest tests/unit/test_agent_delegation_lifecycle.py -q
```

### Backend default regression

```powershell
cd backend
uv run pytest -q
```

### Migration

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
```

### Real API / Runtime

必须提前启动 PostgreSQL、Redis、API、Worker、Scheduler；Gate 不自动管理这些服务。Phase 2.8 B1-B5 完成后必须新增针对 Delegation Runtime 的真实 HTTP + PostgreSQL 验收，而不是用 Unit 或 Mock 替代。

## 8. 当前结论

**当前主线已进入 Phase 2.8 Runtime Integration。Phase 2.7 不再是开发 blocker；Phase 2.8-A Contract、Domain、API、Migration 与 lifecycle 纯规则已建立，但 Worker ownership、实际执行、generation-fenced 写回及多 Worker 真实验收仍未完成。**

下一开发任务不是继续整理文档，而是先修正已发现的 lifecycle 重复规则，然后直接实现 **Phase 2.8-B1 Atomic Delegation Claim**。