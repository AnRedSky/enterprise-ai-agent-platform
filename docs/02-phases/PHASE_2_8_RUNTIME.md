# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。当前进入 Runtime Integration：把 `AgentDelegation` 接入现有 Workflow Worker / lease / fencing 体系，不创建第二套 Worker、Retry 或 Recovery 状态机。

最新代码基线正在推进 **B1 Atomic Delegation Claim**。

## 2. 已完成

- `AgentDelegation` Durable Entity / Repository / Service；
- tenant / source execution / source Agent version / target Agent version lineage；
- stable delegation identity / 幂等；
- depth / active-count / timeout / model budget；
- create/list/get/cancel API；
- Audit / Trace 基础事件；
- active budget creation 的父 Execution 行锁序列化；
- `0038_agent_delegations` Migration；
- `lifecycle.py` 纯生命周期与 Worker fencing 规则入口；
- Service 内重复 lifecycle 规则已删除并统一调用 `lifecycle.validate_transition()`；
- B1 Atomic Claim 初版：PostgreSQL Delegation 行锁、唯一 `worker_execution_id`、复用 `WorkflowExecution` 的既有 Worker owner/lease 字段，并在同一事务中完成 Claim 与 Worker Execution 持久化。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head；它依赖 `0038_agent_delegations`，因此 Phase 2.8 的数据结构基础已经存在。

## 3. Lifecycle Contract

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

`backend/tests/unit/test_agent_delegation_lifecycle.py` 已覆盖状态转换、终态封闭、stale generation、缺失 owner 与 timeout 边界。新增 B1 代码尚未获得开发者本地执行结果，因此不得标记为 Passed。

## 4. B1 Atomic Delegation Claim

B1 已进入代码实现：

```text
pending Delegation
      │
      │ SELECT ... FOR UPDATE
      ▼
唯一数据库 ownership boundary
      │
      ├── timeout / status fail-closed
      ├── 创建既有 WorkflowExecution Worker record
      ├── worker_owner = 当前 Worker
      ├── worker_lease_expires_at = Delegation timeout
      └── delegation.worker_execution_id = Worker Execution.id
      ▼
running Delegation
```

关键约束：

1. Claim 必须带 tenant boundary；
2. 只有 pending 可以 Claim；
3. timeout 到期直接拒绝，不偷偷放宽 lifecycle；
4. Delegation 行锁保证同一时刻只有一个 Worker 获得 ownership；
5. `worker_execution_id` 使用真实 `WorkflowExecution.id`，不生成脱离数据库的伪 identity；
6. Worker lease 复用 `WorkflowExecution.worker_owner / worker_lease_expires_at`，不创建第二套 lease；
7. Delegation 状态和 Worker Execution 创建在同一事务提交，避免半完成 Claim。

## 5. 当前运行时缺口

```text
API create
    ↓
pending Delegation
    ↓  ← B1 已实现，待 PostgreSQL 并发验证
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

### B2 — Workflow Worker Execution Bridge

继续复用现有 Workflow Worker / Execution / lease / fencing，将 target Agent version、model profile、`input_data`、`selected_context_refs`、`allowed_tools` 与 delegation trace identity 显式装配到 Worker execution。不得复制父 Execution 全量 checkpoint、memory 或 credential。

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

### B1 PostgreSQL Integration

B1 必须补充真实 PostgreSQL Integration，至少覆盖：

- 单 Worker Claim；
- 两个并发 Worker Claim 同一 Delegation；
- 已 running / cancelled / terminal Delegation 拒绝；
- timeout 边界拒绝；
- Claim 失败时 Delegation 与 Worker Execution 不产生半完成提交；
- `worker_execution_id` 指向真实 `WorkflowExecution`，且 tenant 一致。

### Real API

B1-B5 完成后增加 Delegation Runtime 专项 Real API Gate，必须覆盖真实 HTTP、PostgreSQL、2+ Worker 并发、stale completion、timeout/cancel 与 Audit/Trace；不得以 Mock 或 Unit 替代。

## 8. 下一交付单元

当前代码交付已经进入 **B1 Atomic Delegation Claim**。下一步不是前端，而是：

```text
B1 targeted Unit
    ↓
B1 PostgreSQL Integration / 2+ Worker concurrency
    ↓
修复真实并发问题
    ↓
B2 Workflow Worker Execution Bridge
```

B1 完成前不扩展 Delegation 前端 UI，也不创建与现有 Worker Runtime 平行的可靠性抽象。
