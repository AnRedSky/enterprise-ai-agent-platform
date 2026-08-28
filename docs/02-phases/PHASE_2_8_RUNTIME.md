# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。B1 Atomic Delegation Claim 已由开发者本地真实 PostgreSQL Gate 验收通过，当前进入 **B2 Workflow Worker Execution Bridge**。

目标仍然是复用现有 Workflow Worker / Execution / lease / fencing / Runtime，不创建第二套 Worker、Retry 或 Recovery 状态机。

## 2. 已完成

- `AgentDelegation` Durable Entity / Repository / Service；
- tenant / source execution / source Agent version / target Agent version lineage；
- stable delegation identity / 幂等；
- depth / active-count / timeout / model budget；
- create/list/get/cancel API；
- Audit / Trace 基础事件；
- active budget creation 的父 Execution 行锁序列化；
- `0038_agent_delegations` Migration；
- `lifecycle.py` 生命周期与 Worker fencing 规则入口；
- B1 Atomic Claim：PostgreSQL Delegation 行锁、唯一 `worker_execution_id`、真实 `WorkflowExecution`、既有 Worker owner/lease 与同事务持久化；
- B1 Real HTTP / PostgreSQL 双 Worker 并发验收，并由开发者本地实际执行通过；
- ORM metadata registry，解决跨模块 ForeignKey 目标表未注册导致的 `NoReferencedTableError`；
- B2 `AgentDelegationRuntimeBridge`，把已 Claim Delegation 显式装配到现有 Worker Runtime。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head。

## 3. Lifecycle Contract

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

B3 将统一补齐结果写回时的 generation fencing；B2 不提前复制第二套 completion 状态机。

## 4. B1 Atomic Delegation Claim

```text
pending Delegation
      │
      │ SELECT ... FOR UPDATE
      ▼
tenant / timeout / lifecycle
      │
      ▼
创建真实 WorkflowExecution
      ├── worker_owner
      ├── worker_lease_expires_at
      └── worker_execution_id
      │
      ▼
Delegation = running
      │
      ▼
Audit + Trace
      │
      ▼
同一事务提交
```

开发者本地最新实际结果：

```text
Model registry Unit       2 passed
Delegation targeted Unit 30 passed
Backend regression        846 passed, 3 skipped, 43 deselected
Migration                 0039_workflow_node_execution_tenant_trigger (head)
Real Delegation Contract  1 passed
B1 PostgreSQL race        1 passed
```

最终：

```text
[PASS] Phase 2.8 Delegation + B1 Atomic Claim gate completed.
```

## 5. B2 Workflow Worker Execution Bridge

B2 的正式桥接路径：

```text
B1 Claim
    ↓
WorkflowExecution.worker_execution_id
    ↓
AgentDelegationRuntimeBridge
    ├── target_agent_version_id
    ├── target_agent_id
    ├── model_profile_id
    ├── input_data
    ├── selected_context_refs
    ├── allowed_tools
    └── trace_id
    ↓
内存 Runtime Version
    ↓
DurableResumeWorkflowRuntime
    ↓
唯一 WorkflowRuntime
    ↓
Target Agent published version
    ↓
ModelGateway / Governance / Provider
```

### 5.1 设计边界

1. B2 不新增 Worker；
2. B2 不新增 Lease；
3. B2 不新增 Retry / Recovery；
4. B2 不写回父 Workflow Version；
5. B2 不复制父 Execution checkpoint、memory 或 credential；
6. target Agent version 必须仍是 tenant 内 published version；
7. `model_profile_id` 必须与 target Agent version 一致；
8. `input_data` 只来自 Delegation 显式输入；
9. `selected_context_refs` / `allowed_tools` 作为显式受治理 Runtime context 装配，不复制 Tool Runtime；
10. `trace_id` 沿 Delegation → Worker Execution 保持一致；
11. 目标 Agent 执行通过现有 ModelGateway / Runtime Governance，不绕过 Provider 治理。

### 5.2 Runtime Version

B2 不创建新的数据库 `WorkflowVersion`。`AgentDelegationRuntimeBridge` 仅在 Worker Runtime 入口构造内存 Runtime Version：

- 保留父 Workflow Runtime timeout / retry / circuit 配置；
- 将单一目标 Agent 作为当前 Worker 的 Runtime Node；
- Node `agent_id` 指向目标 Agent；
- target Agent 的 published version 必须等于 Delegation `target_agent_version_id`；
- Delegation context 只存在本次 Runtime 调用内，不污染父 Workflow Definition。

## 6. B2 自动化验收

新增：

```text
backend/app/services/agent_delegation/runtime_bridge.py
backend/tests/unit/test_agent_delegation_runtime_bridge.py
backend/tests/api_real/test_agent_delegation_bridge_api.py
backend/scripts/test/phase-2.8/02_worker_execution_bridge_gate.ps1
```

B2 Gate 自动执行：

```text
B2 Bridge Unit
    ↓
Backend default regression
    ↓
Alembic upgrade / current
    ↓
自动 PostgreSQL + Redis
    ↓
自动 Backend health / uvicorn
    ↓
自动临时用户注册 + 登录
    ↓
真实 HTTP 创建 Agent / Workflow / Delegation
    ↓
真实 PostgreSQL Claim
    ↓
现有 Worker Runtime Entry
    ↓
Target Agent Runtime
    ↓
真实 PostgreSQL 验证 Worker Execution
```

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

禁止手工填写 Token、用户名、密码、tenant、ID 或测试数据。

## 7. B3/B4/B5

### B3 — Completion / Failure + generation fencing

所有结果写回必须重新锁定 Delegation 并验证 `worker_execution_id` generation。stale Worker、已取消、已超时 Delegation 必须 fail-closed。

### B4 — Timeout / Cancel / Parent semantics

统一复用 Delegation lifecycle；Delegation 自身失败不直接终止父 Execution。

### B5 — Audit / Trace

形成：

```text
source execution
  └── delegation
        └── worker execution / trace
```

要求支持父子反查，metadata 不包含 Secret / credential 原文。

## 8. 验收矩阵

| 场景 | 必须证明 |
|---|---|
| 合法 Claim | pending → running + 唯一 worker generation |
| 并发 Claim | 2+ Worker 竞争仅一个 owner |
| Worker execution | target Agent version 按治理配置真实执行 |
| Context isolation | 只传显式 input/context/tool refs |
| stale completion | 旧 generation 不覆盖当前状态 |
| completed fencing | 终态后 completion 被拒绝 |
| cancel fencing | cancel 后迟到 Worker 不得写回 |
| timeout fencing | timeout 后迟到 Worker 不得写回 |
| Parent semantics | Worker failure 不绕过父 Workflow terminalization |
| Audit / Trace | 子任务可反查父 Execution |
| PostgreSQL | 状态与 generation 在真实数据库中一致 |

## 9. 当前下一步

```text
B2 Unit / Real PostgreSQL Runtime Gate
    ↓
若发现 Runtime / tenant / model profile / context assembly 问题，立即修复
    ↓
B2 验收闭环
    ↓
B3 generation-fenced completion/failure
    ↓
B4 timeout / cancel / parent semantics
    ↓
B5 Audit / Trace
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
```
