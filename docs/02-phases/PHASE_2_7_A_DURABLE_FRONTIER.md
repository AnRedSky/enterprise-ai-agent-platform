# Phase 2.7-A Durable Frontier Contract

> 本文档记录 Phase 2.7-A Closure 后进入 Durable Frontier Scheduling 的生产交付单元。

## 1. 目标

将 Planner 产生的 frontier 从 Runtime 内存结果提升为具有稳定身份、有限生命周期和 PostgreSQL 持久化能力的 Durable Scheduling Contract，逐步接入现有 Scheduler / Worker，而不创建第二套执行体系。

## 2. Frontier Identity

```text
execution_id
+ workflow_version_id
+ decision_fingerprint
+ ordered frontier node ids
        ↓
SHA-256
        ↓
frontier:<digest>
```

Node 顺序必须保留 Planner 的确定性输出。不能把 frontier Node 集合无序化，否则会产生错误的重复 Frontier identity。

## 3. Lifecycle

```text
PENDING
   ↓ claim
CLAIMED
   ↓ start
RUNNING
   ├── success → COMPLETED
   ├── retry   → RETRY_WAIT → CLAIMED
   └── terminal failure → FAILED
```

`COMPLETED` 与 `FAILED` 都是终态，不允许重新 Claim。

## 4. PostgreSQL Durable Frontier

- `WorkflowFrontier` 已建立于 `workflow_frontiers` 表；
- Alembic `0035_workflow_frontier` 已建立表、tenant/key 唯一约束以及 Claim / Execution / Lease 查询索引；
- Frontier 强制保存 tenant、Execution、Workflow Version、Decision fingerprint、ordered node IDs、attempt、Worker lease 和错误事实；
- Repository 不拥有 commit，Scheduler / Worker caller 拥有外层事务。

## 5. 当前 Repository 能力

- `enqueue_frontier()` 使用 `WorkflowFrontierIdentity.key()` + `uq_workflow_frontier_tenant_key` 实现幂等入队；
- 并发唯一键冲突后读取既有 Frontier，不产生第二个 work item；
- `claim_next_frontier()` 使用 tenant scope + `FOR UPDATE SKIP LOCKED`；
- `recover_expired_frontiers()` 回收过期 `claimed/running` Frontier 到 `retry_wait`；
- `transition_owned_frontier()` 同时校验 `worker_owner + attempt` fencing generation，阻止 stale Worker 覆盖新 Worker；
- `renew_owned_frontier_lease()` 使用同一 `worker_owner + attempt` fencing 条件刷新 Frontier lease，不执行 commit。

## 6. Scheduler → Worker 实际接入

本轮已经完成真实生产桥接，不再停留在 Contract：

```text
Scheduled Trigger
   ↓
WorkflowExecution(pending)
   +
WorkflowFrontier(pending)
   ↓
DurableFrontierWorkflowWorker
   ↓
Frontier claim + Execution ownership（同一事务）
   ↓
LeaseAwareWorkflowWorker
   ↓
唯一 WorkflowExecutionService / WorkflowRuntime
   ↓
Execution terminal
   ↓
Frontier terminal
```

Scheduled Trigger 使用 slot idempotency key 创建 Execution 后，在同一调用方事务内创建首个 Frontier。默认 `WorkflowWorker` 已切换为 `DurableFrontierWorkflowWorker`；它不会复制 Runtime，而是复用已有 `LeaseAwareWorkflowWorker` / `WorkflowExecutionService`。

Worker 同时维护 Frontier lease heartbeat 与 Execution lease heartbeat。Frontier terminal transition 必须再次通过 `worker_owner + attempt` fencing；如果旧 Worker 已失去 ownership，则不伪造 Frontier terminal state，等待 lease recovery。

Manual / Webhook Trigger 暂不强制迁移到 Frontier，避免在本阶段改变其公开触发语义；后续统一纳入 Durable Work Item Contract。

## 7. Retry Scheduling

本轮已完成 Durable Frontier Retry Scheduling 基础生产能力：

```text
Runtime retryable failure
        ↓
FrontierRetryPolicy
        ↓
retry_wait
        +
error facts
        +
available_at = now + bounded exponential backoff
        ↓
next Claim
        ↓
attempt + 1
        ↓
new fencing generation
```

实现入口：

- `FrontierRetryPolicy`：提供 `max_attempts`、指数退避和最大延迟边界；
- `schedule_frontier_retry()`：复用当前 Frontier，不创建新的 Execution / Frontier；
- retry transition 继续通过 `transition_owned_frontier()` 校验 `worker_owner + attempt`；
- 当前 attempt 只有在下一次成功 Claim 时递增，retry scheduling 不提前消耗 fencing generation；
- 达到 `max_attempts` 后同一 Frontier 进入 `failed`；
- Retry primitive 不执行 commit，由外层事务统一提交。

### 明确边界

`FrontierRetryPolicy` 不把所有 Runtime `failed` 自动视为 retryable。现有 Runtime error classification 仍是上层责任；Worker integration 必须使用明确的 retryable error classification 后再调用 retry primitive，避免把业务/配置/权限等 terminal failure 无限重试。

## 8. Frontier → Checkpoint → Next Frontier 原子推进

本交付单元已经完成 Durable Progression 基础生产能力：

```text
Worker fencing valid
        ↓
lock current Frontier
        ↓
append next Execution Checkpoint
        ↓
allocate checkpoint sequence under Execution lock
        ↓
idempotent enqueue Next Frontier
        ↓
outer transaction COMMIT
```

实现入口：

- `complete_frontier_with_checkpoint()` 固定锁顺序 `Frontier → Execution/Checkpoint → Next Frontier`；
- 当前 Frontier 必须通过 `worker_owner + attempt` fencing 后才能写入新的 Checkpoint；
- Checkpoint sequence 继续由 `WorkflowExecutionCheckpointService.append_next_in_transaction()` 在 Execution row lock 下分配；
- Next Frontier 必须属于同一 Execution / Workflow Version，并通过 `WorkflowFrontierIdentity` + tenant/key unique constraint 幂等入队；
- Terminal Frontier 可以只追加最终 Checkpoint，不创建后继 Frontier；
- 该 Progression Service 不执行 commit，当前 Frontier、Checkpoint 与 Next Frontier 必须由同一外层事务统一提交；
- 任一阶段失败都必须由调用方回滚，不能留下 `Checkpoint 已写入但 Frontier 未推进` 或 `Frontier 已完成但 Next Frontier 未持久化` 的半状态。

### 锁顺序约束

Worker Claim 已采用 `Frontier → Execution` 的锁顺序，因此 Progression 同样固定先锁当前 Frontier，再进入 Checkpoint/Execution 锁，避免形成反向锁等待链。

### 当前边界

该 primitive 接受 Planner 已确定的 `next_identity`，不在 Persistence 层重新执行 DAG 条件求值、State Merge 或 Planner。下一阶段必须在真实 Runtime/DAG Planner integration 中提供确定性 Next Frontier，并继续复用唯一 Planner/Runtime。

## 9. 当前剩余主线

```text
Durable Frontier Scheduling
   ├── Scheduler → Frontier enqueue        ✅
   ├── Frontier → Worker claim             ✅
   ├── Worker → Runtime bridge             ✅
   ├── Frontier lease heartbeat            ✅
   ├── Retry scheduling                    ✅
   ├── Frontier → Checkpoint progression  ✅
   ├── Next Frontier idempotent enqueue    ✅
   └── Runtime/Planner progression wiring  ⏭
```

下一交付单元不再扩展 Frontier Persistence primitive，而是把 `complete_frontier_with_checkpoint()` 接入真实 Runtime/DAG Planner 成功路径：Planner 输出 deterministic next frontier，Runtime 在同一 Execution transaction 中固化 checkpoint 并推进后继 Frontier。

## 10. 测试边界

当前只保留 Unit Test Contract；本环境未实际执行 pytest，因此不得记录 Unit Test PASS。Real API 后续必须实际验证 PostgreSQL 持久化以及 Scheduler → Frontier → Worker → Runtime → Retry → Checkpoint → Next Frontier 生命周期。