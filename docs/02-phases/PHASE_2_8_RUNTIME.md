# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。当前进入 Runtime Integration：把 `AgentDelegation` 接入现有 Workflow Worker / lease / fencing 体系，不创建第二套 Worker、Retry 或 Recovery 状态机。

当前代码已进入 **B1 Atomic Delegation Claim**，并完成第一版生产实现与自动化验收测试实现。

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
- B1 Atomic Claim：PostgreSQL Delegation 行锁、唯一 `worker_execution_id`、复用 `WorkflowExecution` 的既有 Worker owner/lease 字段，并在同一事务中完成 Claim 与 Worker Execution 持久化；
- B1 Real API / PostgreSQL 双 Worker 并发验收测试实现；
- Phase 2.8 Gate 已纳入 B1 lifecycle Unit、Backend regression、Migration、Delegation Real API 与 PostgreSQL 两 Worker race。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head；它依赖 `0038_agent_delegations`，因此 Phase 2.8 的数据结构基础已经存在。

## 3. Lifecycle Contract

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

`backend/tests/unit/test_agent_delegation_lifecycle.py` 已覆盖状态转换、终态封闭、stale generation、缺失 owner 与 timeout 边界。

## 4. B1 Atomic Delegation Claim

B1 已进入代码实现：

```text
pending Delegation
      │
      │ SELECT ... FOR UPDATE
      ▼
唯一数据库 ownership boundary
      │
      ├── tenant scope
      ├── timeout / status fail-closed
      ├── 创建既有 WorkflowExecution Worker record
      ├── worker_owner = 当前 Worker
      ├── worker_lease_expires_at = Delegation timeout
      └── delegation.worker_execution_id = Worker Execution.id
      ▼
running Delegation
      │
      ├── Audit
      └── Trace
      │
      ▼
同一事务提交
```

关键约束：

1. Claim 必须带 tenant boundary；
2. 只有 pending 可以 Claim；
3. timeout 到期直接拒绝，不偷偷放宽 lifecycle；
4. Delegation 行锁保证同一时刻只有一个 Worker 获得 ownership；
5. `worker_execution_id` 使用真实 `WorkflowExecution.id`，不生成脱离数据库的伪 identity；
6. Worker lease 复用 `WorkflowExecution.worker_owner / worker_lease_expires_at`，不创建第二套 lease；
7. Delegation 状态和 Worker Execution 创建在同一事务提交，避免半完成 Claim；
8. B1 不执行 target Agent Runtime，执行桥接留给 B2。

## 5. B1 自动化验收实现

新增：

```text
backend/tests/api_real/test_agent_delegation_claim_api.py
```

该测试通过真实 HTTP 创建 Delegation，然后使用两个独立 PostgreSQL `AsyncSession` 并发竞争同一个 Delegation，验证：

- 恰好一个 Worker Claim 成功；
- Delegation 最终为 `running`；
- `worker_execution_id` 指向唯一真实 `WorkflowExecution`；
- Worker owner 与成功 Claim 对应；
- tenant identity 一致；
- 第二次 Claim 被拒绝。

Phase 2.8 Gate：

```text
Unit lifecycle / identity
    ↓
Backend default regression
    ↓
Alembic upgrade head / current
    ↓
Delegation Real HTTP + PostgreSQL
    ↓
B1 PostgreSQL two-worker race
```

当前测试实现只能证明“已具备自动化验证入口”，不能代替开发者实际本地执行结果。

## 6. 当前运行时缺口

```text
API create
    ↓
pending Delegation
    ↓
B1 Atomic Claim
    │
    ├─ 已实现
    └─ 待开发者本地 PostgreSQL 验证
    ↓
running + worker_execution_id
    ↓
B2 Existing Worker Execution bridge
    ↓
Agent Runtime
    ↓
B3 generation-fenced completion/failure
    ↓
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

## 7. 验收矩阵

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

## 8. 本地测试入口

### B1 一键 Gate

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

### B1 Unit / Backend / Migration，不执行 Real API

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1 -SkipRealApi
```

### B1 Real API + PostgreSQL + 双 Worker

前置条件：

1. PostgreSQL 已启动；
2. Backend 已安装依赖；
3. `backend/.env` 或 `.env.local` 已配置本地数据库；
4. 数据库已执行到 Alembic head；
5. Backend HTTP 服务已启动；
6. 使用开发者本地有效 Token，不提交 Token。

PowerShell：

```powershell
cd backend
$env:ACCESS_TOKEN = "<开发者本地有效 Token>"
$env:API_BASE_URL = "http://127.0.0.1:8000/api/v1"

uv run alembic upgrade head
uv run alembic current

uv run pytest -q tests/api_real/test_agent_delegation_api.py
uv run pytest -q tests/api_real/test_agent_delegation_claim_api.py
```

完整 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\01_delegation_contract_gate.ps1
```

验收必须看到 B1 两 Worker race 测试实际执行成功；若 PostgreSQL、Token、HTTP 服务或测试任一步失败，只记录实际失败原因，不得记录为 Passed。

## 9. 下一交付单元

B1 自动化测试入口已经完成。待开发者本地真实 PostgreSQL Gate 验证后，下一生产代码交付直接进入：

```text
B1 本地验证 / 并发问题修复
    ↓
B1 验收闭环
    ↓
B2 Workflow Worker Execution Bridge
    ↓
B3 completion / failure + generation fencing
```

B1 完成前不扩展 Delegation 前端 UI，也不创建与现有 Worker Runtime 平行的可靠性抽象。
