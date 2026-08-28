# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。B1 Atomic Delegation Claim、B2 Workflow Worker Execution Bridge、B3 generation-fenced completion/failure 已由开发者本地真实 PostgreSQL Gate 验收通过，当前进入 **B4 Timeout / Cancel / Parent semantics**。

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
- B2 `AgentDelegationRuntimeBridge`，把已 Claim Delegation 显式装配到现有 Worker Runtime；
- B3 completion/failure generation fencing；
- B2/B3 Runtime Session、terminalization、lease race 与 frontier lock-order 问题修复；
- Scheduler 单节点顺序 Workflow 的空 `edges` 语义修复。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head。

## 3. Lifecycle Contract

```text
pending → running / cancelled
running → completed / failed / timed_out / cancelled
terminal → 不允许再次进入活动态
Worker completion → running + 当前 worker_execution_id generation 必须一致
timeout → now >= timeout_at
```

## 4. B1/B2/B3 本地证据

最新开发者本地结果：

```text
B2 bridge Unit             3 passed
Backend regression         853 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               3 passed

B3 lifecycle Unit          30 passed
Backend regression         853 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B3 Real Gate               3 passed
```

此前 `AgentDelegation=running` 与 `WorkflowExecution=completed` 的 finalization race，以及 Frontier heartbeat `Frontier → Execution` 反向锁序导致的 PostgreSQL deadlock，已完成代码修复并通过当前 B2/B3 Gate。

## 5. B4 Timeout / Cancel / Parent semantics

### 5.1 Delegation timeout

新增 `agent_delegation.timeout` 正式运行时规则：

```text
Workflow Runtime timeout
        ↓
Delegation remaining timeout
        ↓
取两者较小值
        ↓
Worker Runtime asyncio timeout
        ↓
子 Worker Execution → cancelled
        ↓
Runtime Session 完整退出
        ↓
独立 Delegation Session
        ↓
Delegation → timed_out
```

关键约束：

1. `timeout_at` 是 Delegation 生命周期的持久化边界；
2. Delegation timeout 不直接终止父 Workflow Execution；
3. 子 Worker Execution 只使用既有 `WorkflowExecutionService.transition(..., "cancelled")`；
4. Delegation `timed_out` 写入使用独立 Session，并继续验证 tenant + `worker_execution_id` generation；
5. timeout 后任何迟到 completion/failure 都因 Delegation 已进入 terminal 状态而 fail-closed；
6. 不新增第二套 Retry / Recovery 状态机。

### 5.2 Cancel

```text
pending → cancelled
running → cancelled
```

API 取消只修改 Delegation 生命周期，不直接把父 Workflow Execution 推入 terminal 状态。重复取消、终态取消均 fail-closed。

### 5.3 Parent semantics

```text
Worker completed / failed / timed_out / cancelled
        ↓
Delegation 自身终态
        ↓
父 Workflow Execution 继续由既有 Workflow / Execution / Retry / Recovery Contract 决定
```

Worker failure、timeout、cancel 不允许绕过父 Execution 状态机直接写父 Execution terminal 状态。

## 6. B4 自动化验收

新增：

```text
backend/app/services/agent_delegation/timeout.py
backend/tests/unit/test_agent_delegation_timeout.py
backend/tests/api_real/test_agent_delegation_b4_api.py
backend/scripts/test/phase-2.8/04_delegation_timeout_cancel_gate.ps1
```

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\04_delegation_timeout_cancel_gate.ps1
```

Gate 只验证本地前置服务，不启动、重启或停止服务；测试用户、Token、tenant、ID 与测试数据均由 Gate 自动生成。

验收顺序：

```text
B4 timeout Unit
    ↓
Backend regression
    ↓
Alembic upgrade/head
    ↓
真实 HTTP + PostgreSQL cancel
    ↓
真实 PostgreSQL Claim
    ↓
真实 Worker Runtime timeout
    ↓
验证 child cancelled + delegation timed_out
    ↓
验证 parent Execution 未进入 terminal
```

## 7. B5

B5 将在 B4 Real Gate 通过后进入：

```text
source execution
  └── delegation
        └── worker execution / trace
```

要求支持父子反查、completed/failed/timed_out/cancelled 全生命周期 Audit / Trace closure，metadata 不包含 Secret / credential 原文。

## 8. 当前下一步

```text
B4 Timeout / Cancel / Parent semantics
    ↓
B4 Real Gate 本地验收
    ↓
B5 Audit / Trace closure
    ↓
Delegation 多 Worker + PostgreSQL + Runtime acceptance
    ↓
Phase 2.8 closure
```
