# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。当前进入 Runtime Integration：把 `AgentDelegation` 接入现有 Workflow Worker / lease / fencing 体系，不创建第二套 Worker、Retry 或 Recovery 状态机。

最新 `main`：`f080ff53d1f5b5f5352ad36fc0be1d8e6d08e9e7`。

## 2. 已完成

- `AgentDelegation` Durable Entity / Repository / Service；
- tenant / source execution / source Agent version / target Agent version lineage；
- stable delegation identity / 幂等；
- depth / active-count / timeout / model budget；
- create/list/get/cancel API；
- Audit / Trace 基础事件；
- active budget creation 的父 Execution 行锁序列化；
- `0038_agent_delegations` Migration；
- `lifecycle.py` 纯生命周期与 Worker fencing 规则入口。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head；它依赖 `0038_agent_delegations`，因此 Phase 2.8 的数据结构基础已经存在。

## 3. Lifecycle Contract

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

`backend/tests/unit/test_agent_delegation_lifecycle.py` 已覆盖状态转换、终态封闭、stale generation、缺失 owner 与 timeout 边界，但 `37061ab` 之后尚无新的开发者本地执行结果，因此保持“待验证”。

## 4. 深度核查发现

`lifecycle.py` 已作为正式生命周期规则入口，但 `AgentDelegationService` 仍复制 `TERMINAL_STATES` / `TRANSITIONS`，`cancel()` 直接使用副本。当前两套规则内容一致，但形成重复业务规则入口，违反单一规则入口原则。

**B1 开发前必须先删除 Service 内重复规则并统一调用 `lifecycle.validate_transition()`；该问题已记录到 `docs/04-errors/`。**

## 5. 当前运行时缺口

```text
API create
    ↓
pending Delegation
    ↓  ← B1 Atomic Claim
running + worker_execution_id
    ↓  ← B2 Existing Worker Execution bridge
Agent Runtime
    ↓  ← B3 generation-fenced completion/failure
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace closure
    ↓
Real API + PostgreSQL + multi-worker acceptance
```

### B1 — Atomic Delegation Claim

仅 `pending` 可 Claim；使用 PostgreSQL 条件更新或行锁形成唯一 ownership boundary；生成唯一 `worker_execution_id`；2+ Worker 并发竞争只能一个 generation 成功；timeout/cancel/terminal 状态必须 fail-closed；不新增独立 Worker lease。

### B2 — Workflow Worker Execution Bridge

复用既有 Workflow Worker / Execution / lease / fencing，将 target Agent version、model profile、`input_data`、`selected_context_refs`、`allowed_tools` 与 delegation trace identity 显式装配到 Worker execution。不得复制父 Execution 全量 checkpoint、memory 或 credential。

### B3/B4 — Completion / Failure / Timeout / Cancel

所有结果写回必须经过统一 lifecycle rule，并在事务内重新确认 `worker_execution_id`。stale Worker、已取消 Delegation、已超时 Delegation 均必须 fail-closed。Delegation 自身失败不直接终止父 Execution。

### B5 — Audit / Trace

形成：

```text
source execution
  └── delegation
        └── worker execution / trace
```

要求支持父子反查，且 metadata 不得包含 Secret / credential 原文。

## 6. 验收矩阵

| 场景 | 必须证明 |
|---|---|
| 合法 Claim | pending → running + 唯一 worker generation |
| 并发 Claim | 2+ Worker 竞争仅一个 owner |
| stale completion | 旧 generation 不覆盖当前状态 |
| completed fencing | 终态后 completion 被拒绝 |
| cancel fencing | cancel 后迟到 Worker 不得写回 |
| timeout fencing | timeout 后迟到 Worker 不得写回 |
| Worker execution | target Agent version 按治理配置真实执行 |
| Context isolation | 只传显式 input/context/tool refs |
| Parent semantics | Worker failure 不绕过父 Workflow terminalization |
| Audit / Trace | 子任务可反查父 Execution |
| PostgreSQL | 状态与 generation 在真实数据库中一致 |

## 7. 本地测试入口

### Lifecycle Unit

```powershell
cd backend
uv run pytest tests/unit/test_agent_delegation_lifecycle.py -q
```

### Backend Regression

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

### Real API

B1-B5 完成后增加 Delegation Runtime 专项 Real API Gate，必须覆盖真实 HTTP、PostgreSQL、2+ Worker 并发、stale completion、timeout/cancel 与 Audit/Trace；不得以 Mock 或 Unit 替代。

## 8. 下一交付单元

下一次代码交付以 **“唯一 lifecycle 入口修正 + B1 Atomic Delegation Claim + Unit/Integration”** 为最小完整交付单元。B1 完成前不扩展 Delegation 前端 UI，也不创建与现有 Worker Runtime 平行的可靠性抽象。
