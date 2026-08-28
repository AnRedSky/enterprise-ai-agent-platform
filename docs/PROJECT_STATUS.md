# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前代码基线：`5ecf427a` — `fix(worker): reconcile terminal execution after lease race`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B2 Worker Execution Bridge Real Gate 修复与本地验收**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力已完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施已完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- lifecycle / Worker fencing 纯规则入口已建立；
- B1 Atomic Claim 已完成生产实现，并已通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已进入生产代码，复用现有 Workflow Worker / WorkflowRuntime 执行目标 Agent version；
- B3 Delegation completion/failure 已进入生产代码，以 `worker_execution_id` 作为 Worker generation fencing identity；
- Runtime Session / Execution terminalization / Model Profile Snapshot 前置问题已完成修复；
- Delegation terminal write 已完成 tenant + running + worker generation fencing 与 ORM bulk DML 边界整改。

## 3. 最新本地验收反馈

开发者在 `5d1963d3` 基线执行 B2 Gate：

```text
B2 bridge Unit             3 passed
Backend regression         850 passed, 3 skipped, 46 deselected
Migration/head             0039_workflow_node_execution_tenant_trigger (head)
B2 Real Gate               1 failed, 2 passed
```

失败仍为：

```text
assert persisted.status == "completed"
E AssertionError: assert 'running' == 'completed'
```

同时真实 Worker Service 日志出现 PostgreSQL `DeadlockDetectedError`，调用点为 Durable Frontier `renew_owned_frontier_lease()` 更新 `workflow_executions.worker_lease_expires_at`。

## 4. 本轮修复

### 4.1 B2 Lease Lost / Runtime terminalization 竞态

`execute_claimed_execution()` 不再在捕获 `WorkflowWorkerLeaseLost` 后无条件 `return`。该异常可能发生在 Runtime 已经把 Workflow Execution 持久化为 `completed/failed`、随后 heartbeat 执行 ownership fencing UPDATE 并观察到 `rowcount=0` 的竞态窗口。

现在捕获 Lease Lost 后使用独立 Session 重新读取 durable Execution：

- `completed`：恢复 completed outcome，继续 Delegation finalization；
- `failed`：恢复 failed outcome 与持久化错误码，继续 Delegation finalization；
- `pending/running`：确认 Runtime 尚未终态化，才保持 `WORKER_LEASE_LOST` 并放弃本 generation；
- 不存在：安全放弃，不伪造完成事实。

这直接消除了此前形成 `WorkflowExecution=completed / AgentDelegation=running` 的竞态窗口。

### 4.2 Durable Frontier heartbeat 反向锁序

`renew_owned_frontier_lease()` 原来为 `Frontier → Execution`，而 `claim_next_frontier()` 已采用 `Execution → Frontier`。本轮将 heartbeat 改为统一的：

```text
读取 Frontier execution_id
        ↓
Execution UPDATE
        ↓
Frontier UPDATE
```

任一层 ownership / attempt / status / lease 校验失败都会 rollback 两层续租，避免半续租状态，并消除 heartbeat 与 Claim/terminalization 的反向锁序。

## 5. B2 当前运行链路

```text
B1 Claim
    ↓
WorkflowExecution.worker_execution_id
    ↓
AgentDelegationRuntimeBridge
    ↓
单 Node 内存 Runtime Version
    ↓
既有 DurableResumeWorkflowRuntime
    ↓
既有 WorkflowRuntime
    ↓
Workflow Execution terminalization
    ↓
Runtime Session async with 完整退出
    ↓
Lease Lost race reconciliation（仅在 heartbeat 与 terminalization 同时发生时）
    ↓
独立 Delegation finalization Session
    ↓
tenant + worker_execution_id fencing
    ↓
Delegation completed / failed + AuditLog + WorkflowTraceEvent
```

## 6. B3 当前实现

B3 不允许旧 Worker generation 修改新 generation 的 Delegation 状态。completion/failure 仍要求当前 Worker Execution generation 匹配；Lease Lost 只有在 durable Execution 尚未进入终态时才提前放弃。

## 7. 自动化验收

B2 正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

Gate 只验证本地前置服务，不自动启动、重启或停止服务；测试用户、密码、Access Token 与测试数据均由 Gate 自动生成，不要求手工填写测试信息。

要求的前置服务：

- PostgreSQL：Docker Compose `postgres`；
- Redis：Docker Compose `redis`；
- Backend HTTP API：`http://127.0.0.1:8000/health` 可访问。

Gate 内部顺序：

```text
[0] prerequisite service verification
    ↓
[1] B2 bridge Unit
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head verification
    ↓
[4] Real HTTP + PostgreSQL B2/B3 Gate
```

## 8. 当前验证状态

本轮代码已经针对最新失败的真实并发根因完成修复，但当前环境无法替代开发者本地 PostgreSQL/Worker Service 实际运行，因此**不得预填 B2 已通过**。

下一步必须由开发者重新执行 B2 Gate，并在真实 Worker Service 持续运行条件下观察 heartbeat。只有以下条件全部满足后，B2 才能标记完成：

1. B2 Real Gate 通过，`AgentDelegation.status == completed`；
2. B3 stale generation fencing 继续通过；
3. Worker heartbeat 不再出现该 `Frontier → Execution` 反向锁序导致的 deadlock；
4. Backend Regression 无新增失败；
5. Migration head 保持 `0039_workflow_node_execution_tenant_trigger`。

对应错误记录：`docs/04-errors/2026-08-28-b2-delegation-finalization-session-lifetime.md`。
