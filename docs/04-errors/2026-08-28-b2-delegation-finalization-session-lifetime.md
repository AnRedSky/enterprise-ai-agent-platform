# B2 Delegation 终态收敛与 Worker Lease 并发边界

## 1. 现象

Phase 2.8 B2 Worker Execution Bridge Real Gate 中，Worker Execution 已成功进入 `completed`，真实 PostgreSQL 查询也能读取 completed Execution 与目标 Agent 输出，但对应 `AgentDelegation.status` 仍为 `running`。

同时，在真实 Worker Service 运行期间出现 PostgreSQL `DeadlockDetectedError`，冲突 SQL 为刷新 `workflow_executions.worker_lease_expires_at`，调用链位于 Durable Frontier lease heartbeat。

## 2. 根因一：Lease Lost 与 Runtime Terminalization 竞态

此前已经把 Delegation finalization 移出 Runtime Session，但仍存在一个没有覆盖到的并发窗口：

```text
Runtime Task
    │
    ├─ 将 WorkflowExecution 持久化为 completed
    │  └─ 清理 worker ownership
    │
Lease Monitor Task
    │
    └─ 紧接着执行 ownership fencing UPDATE → rowcount = 0
                                      ↓
                             WorkflowWorkerLeaseLost
                                      ↓
                         execute_claimed_execution return
                                      ↓
                         Delegation finalization 未执行
```

`WorkflowWorkerLeaseGuard` 的职责是：明确失去 ownership 时取消 Runtime；因此它不能把数据库已经完成的 Execution 重新解释为未完成。但在 Runtime terminalization 与 heartbeat 同时到达时，Lease Monitor 可能先观察到 `rowcount = 0`，从而触发 `WorkflowWorkerLeaseLost`。

此前实现直接 `return`，没有重新读取 durable Execution 状态，于是形成：

```text
WorkflowExecution = completed
AgentDelegation   = running
```

这正是 B2 Real Gate 持续重复失败的真正剩余根因。此前多轮 Session、ORM DML 与 transaction boundary 修复只解决了“怎么写”，没有解决“Runtime 已经写完而 heartbeat 同时判定 ownership 丢失”的竞态。

## 3. 根因二：Durable Frontier heartbeat 反向锁序

`claim_next_frontier()` 已明确采用：

```text
Execution → Frontier
```

以避免 Claim 与 terminalization 的反向锁等待。

但旧 `renew_owned_frontier_lease()` 顺序是：

```text
Frontier UPDATE
    ↓
Execution UPDATE
```

因此 heartbeat 与 Claim/其他 terminalization 可以形成：

```text
Transaction A: Frontier → waits Execution
Transaction B: Execution → waits Frontier
```

PostgreSQL 最终检测为 deadlock。用户真实 Worker 日志已经提供了明确证据：`renew_owned_frontier_lease()` 在更新 `workflow_executions` 时收到 `DeadlockDetectedError`。

## 4. 本轮修复

### 4.1 B2 terminalization race reconciliation

`execute_claimed_execution()` 在捕获 `WorkflowWorkerLeaseLost` 后重新建立独立数据库 Session，读取当前 Worker Execution durable state：

- `completed`：说明 Runtime 已经正常完成，只是 heartbeat 在 terminalization 边界观察到了 ownership 已清理；恢复 `outcome=completed`，继续执行 Delegation finalization；
- `failed`：说明 Runtime 已经持久化失败，恢复 `outcome=failed` 与已有错误码，继续执行 Delegation failure finalization；
- `pending/running`：说明 Runtime 并未完成，保持 `WORKER_LEASE_LOST` 语义并放弃本 generation 的 Delegation 收敛；
- Execution 不存在：保持安全失败，不伪造完成事实。

因此“lease lost”不再被机械等价为“execution 未完成”，而是以 PostgreSQL durable terminal fact 为最终判断依据。

### 4.2 Durable Frontier heartbeat lock ordering

`renew_owned_frontier_lease()` 改为：

```text
只读 Frontier → 取得 execution_id
        ↓
Execution UPDATE（ownership fencing）
        ↓
Frontier UPDATE（attempt + ownership fencing）
```

这样 heartbeat 与 Frontier Claim 统一采用 `Execution → Frontier` 锁序；任一层校验失败都会 rollback 两层续租，避免产生半续租状态。

## 5. 为什么此前修复没有解决

此前修复链条分别处理了：

1. ORM bulk terminal DML identity ambiguity；
2. returned entity / fencing write；
3. Runtime Session 与 finalization Session 隔离；
4. `async with` 生命周期真正退出后再 finalization。

这些修复都是真问题，但 B2 仍然失败的最后一个条件是并发竞态，而不是单纯 Session 生命周期问题。只看最终数据库状态而不分析 Lease Guard 的任务竞争关系，就会继续重复修改 finalization SQL，却无法覆盖这个窗口。

## 6. 验证要求

必须由开发者在本地真实环境重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

并额外保持一个真实 Worker Service 运行，验证 heartbeat 不再持续输出 `DeadlockDetectedError`。

重点验收：

- B2 bridge Unit 全部通过；
- Backend default regression 无新增失败；
- Alembic head 保持 `0039_workflow_node_execution_tenant_trigger`；
- B2 Real HTTP + PostgreSQL 中 `WorkflowExecution.status == completed`；
- `AgentDelegation.status == completed`；
- `AgentDelegation.ended_at` 非空；
- 目标 Agent / Agent Version 输出正确；
- B3 stale generation fencing 保持 409；
- Durable Frontier Worker 连续 heartbeat 不再出现该锁序导致的 deadlock。

本记录不预填“通过”；最终状态必须以开发者实际执行结果为准。
