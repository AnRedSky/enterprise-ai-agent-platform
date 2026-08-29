# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B6 Delegation Multi-Worker Runtime acceptance**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- B4 timeout / cancel / parent semantics 已完成并由开发者本地 Real Gate 验收通过；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成并通过 B5 Unit Gate。

## 3. 最新本地验收证据

开发者在 `352f737a` 基线完成 B5：

```text
B5 Worker shutdown + Delegation lifecycle Unit   27 passed
Backend regression                                860 passed, 3 skipped, 50 deselected
Migration/head                                   0039_workflow_node_execution_tenant_trigger (head)
B5 Real Gate                                     4 passed
```

B5 已达到本地 Gate 通过条件，允许进入多 Worker Runtime acceptance。

## 4. B6 实现目标

此前 B1 Claim 创建 `WorkflowExecution` 后没有进入 Durable Frontier。由于默认 `run_worker.py` 使用 Durable Frontier 作为唯一 dispatch 入口，直接调用 `execute_claimed_execution()` 的测试可以通过，但独立 Worker 无法发现该 Delegation Execution。

本任务已修复为：

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

Claim、Worker Execution、Frontier 与 Claim Audit/Trace 在同一事务中提交；Frontier fingerprint 同时绑定 Delegation 与 Worker Execution generation。

## 5. B6 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、ID 与测试数据；Gate 本身不启动、重启或停止任何服务，只验证 PostgreSQL、Redis、Backend API 等本地前置服务。

验收顺序：

```text
[0] prerequisite service verification
    ↓
[1] Delegation Runtime Unit/Contract
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
```

B6 Real Gate 必须实际证明：

1. Delegation Claim 同事务创建 Durable Frontier；
2. 两个独立 Worker 实例均可通过正式 `dispatch_once()` 消费 Delegation Frontier；
3. Worker Execution、Frontier、Delegation 三者终态一致；
4. 同一 Delegation 只有一个 `worker_execution_id`；
5. Frontier 与 Execution 使用同一 worker owner；
6. 父 Workflow Execution 不因子 Delegation 完成而进入终态；
7. 真实 PostgreSQL 持久化链路成立。

**B6 代码已实现，但本执行环境无法连接用户本地 PostgreSQL/Backend，因此不得预填 B6 Passed。**

## 6. 下一主线任务

```text
B6 Delegation Multi-Worker Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```
