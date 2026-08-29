# Phase 2.8 Delegation Runtime Integration — Worker 生命周期与执行闭环

## 1. 当前状态

Phase 2.8-A Contract 已冻结，Delegation Domain + API + Migration 已实现。B1 Atomic Delegation Claim、B2 Workflow Worker Execution Bridge、B3 generation-fenced completion/failure、B4 timeout/cancel/parent semantics 与 B5 Audit/Trace 基础闭环均已实现并由开发者本地 Gate 验收通过，当前进入 **B6 Multi-Worker Runtime acceptance**。

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
- B4 timeout/cancel/parent semantics；
- B5 Delegation Audit/Trace 基础闭环；
- Worker shutdown AsyncEngine cancellation-safe disposal；
- Scheduler 单节点顺序 Workflow 的空 `edges` 语义修复。

`0039_workflow_node_execution_tenant_trigger` 当前为数据库 head。

## 3. B5 本地验收

开发者在 `352f737a` 基线完成 B5：

```text
B5 Worker shutdown + Delegation lifecycle Unit   27 passed
Backend regression                                860 passed, 3 skipped, 50 deselected
Migration/head                                   0039_workflow_node_execution_tenant_trigger (head)
B5 Real Gate                                     4 passed
```

B5 已通过本地验收。

## 4. B6 Multi-Worker Runtime 问题与修复

B1 原实现只创建 `WorkflowExecution`，没有创建 `WorkflowFrontier`。默认 `run_worker.py` 已使用 Durable Frontier 作为唯一 dispatch 入口，因此 B2 直接调用 Runtime 的测试虽然能够执行，独立 Durable Frontier Worker 却无法发现 Delegation Execution。

修复后的 Claim 闭环为：

```text
Delegation Claim
    ↓
WorkflowExecution
    ↓
Durable Frontier(delegation.target)
    ↓
Durable Frontier Worker
    ↓
AgentDelegationRuntimeBridge
    ↓
既有 WorkflowRuntime
    ↓
Delegation terminalization
```

Frontier identity 使用 Delegation + Worker Execution generation 生成确定性 fingerprint，Claim、Worker Execution、Frontier 与 Claim Audit/Trace 在同一事务中提交。

## 5. B6 自动化验收

新增：

```text
backend/tests/api_real/test_agent_delegation_multi_worker_api.py
backend/scripts/test/phase-2.8/06_delegation_multi_worker_runtime_gate.ps1
```

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、ID 与测试数据；Gate 本身不启动、重启或停止任何服务，只验证本地 PostgreSQL、Redis、Backend API 前置条件。

验收顺序：

```text
B6 targeted Unit/Contract
    ↓
Backend regression
    ↓
Alembic upgrade/head
    ↓
真实 HTTP + PostgreSQL
    ↓
两个独立 Worker 实例 dispatch_once
    ↓
Delegation / Worker Execution / Frontier 终态闭环
    ↓
父 Workflow Execution 保持非终态
```

测试使用两个 `WorkflowWorker` 实例、每个并发度 1，分两轮并发 dispatch，确保每轮最多由两个 Worker 各消费一个 Durable Frontier；所有 Delegation 必须最终完成，且每个 Delegation 只存在一个 Worker Execution。

## 6. 下一步

```text
B6 Multi-Worker Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```

B6 代码完成后必须由开发者本地执行 Gate，实际通过后才能标记 B6 Passed 并进入 Phase 2.8 closure。
