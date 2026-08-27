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

```text
Scheduled Trigger
   ↓
WorkflowExecution(pending)
   +
WorkflowFrontier(pending)
   ↓
PlannerDrivenDurableFrontierWorkflowWorker
   ↓
Frontier claim + Execution ownership
   ↓
唯一 WorkflowExecutionService / WorkflowRuntime
   ↓
当前 Planner frontier Node execution
   ↓
Checkpoint facts
   ↓
当前 Frontier terminal + Next Frontier enqueue
```

默认 `WorkflowWorker` 已切换为 `PlannerDrivenDurableFrontierWorkflowWorker`。该 Worker 继承既有 `DurableFrontierWorkflowWorker` 的 Claim / Lease / Dispatch 契约，并只编排一次 Planner frontier，不复制 Runtime、Planner、Checkpoint 或 Retry 算法。

历史 Scheduled Trigger 首个 Frontier 可能保存完整 Node 集合作为 bootstrap work item。首次 Durable dispatch 允许从该记录中按 Planner root 实际执行；从第二个 Frontier 开始必须与 Planner 输出严格一致。该兼容逻辑仅用于历史记录收敛，不扩展为新的长期 Contract。

Worker 同时维护 Frontier lease heartbeat 与 Execution lease heartbeat。Frontier terminal transition 必须再次通过 `worker_owner + attempt` fencing；如果旧 Worker 已失去 ownership，则不伪造 Frontier terminal state，等待 lease recovery。

Manual / Webhook Trigger 暂不强制迁移到 Frontier，避免在本阶段改变其公开触发语义；后续统一纳入 Durable Work Item Contract。

## 7. Retry Scheduling

已完成 Durable Frontier Retry Scheduling 基础生产能力：

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

### 7.1 Runtime 异常路径收敛

Planner-driven Worker 已将 Runtime 异常正式接入 Frontier Retry / Failed 生命周期：

```text
Runtime dispatch
      ↓ exception
rollback Runtime transaction
      ↓
failure classification
   ├── transient → retry_wait + available_at + error facts
   │                 ↓
   │             release Execution ownership
   │
   └── terminal → Frontier failed + Execution failed
```

明确临时故障包括 HTTP 408 / 429 / 5xx、TimeoutError、ConnectionError 与 CircuitOpenError；Planner/Contract/其他业务异常默认进入终态失败。Retry policy 读取 Workflow `config.retry_budget`，retry exhausted 时同一 Frontier 与 Execution 一起进入 `failed`。

异常收敛使用独立补偿事务：Runtime 原事务先 rollback，避免半完成 Node facts 与 Retry 状态拆分提交；补偿事务重新锁定同一 tenant scope 下的 Frontier / Execution 后完成状态收敛和 Worker ownership 释放。expired lease recovery 仅作为 Worker 丢失 ownership 的恢复机制，不再承担正常 Runtime Retry 职责。

## 8. Frontier → Checkpoint → Next Frontier 原子推进

已进入真实 Planner-driven Worker 路径，并进一步收敛为统一 Progression primitive：

```text
Worker fencing valid
        ↓
Runtime executes current Planner frontier
        ↓
Runtime Node facts
        ↓
complete_frontier_with_checkpoint()
        ├── fencing transition current Frontier
        ├── append Checkpoint in same transaction
        ├── idempotent enqueue Next Frontier
        └── caller COMMIT
```

基础 Persistence API：

- `complete_frontier_with_checkpoint()` 固定 Frontier → Execution/Checkpoint → Next Frontier 的锁顺序；
- 当前 Frontier 必须通过 `worker_owner + attempt` fencing 后才能写入新的 Checkpoint；
- Checkpoint sequence 继续由 `WorkflowExecutionCheckpointService.append_next_in_transaction()` 在 Execution row lock 下分配；
- Next Frontier 必须属于同一 Execution / Workflow Version，并通过 `WorkflowFrontierIdentity` + tenant/key unique constraint 幂等入队；
- Terminal Frontier 可以只追加最终 Checkpoint，不创建后继 Frontier；
- Persistence primitive 不执行 commit，外层调用方负责事务提交。

### 8.1 Planner-driven Runtime Integration

`PlannerDrivenDurableFrontierWorkflowWorker` 是默认 Worker 正式入口。Worker 已实际调用 `complete_frontier_with_checkpoint()`，因此 Frontier terminal、Checkpoint、Next Frontier 不再由 Worker 分别写入。

对于 DAG：

```text
Planner frontier
      ↓
Node / Multi-frontier execution
      ↓
Durable Node facts
      ↓
Checkpoint progression primitive
      ↓
Planner rebuild
      ↓
Next frontier
```

对于无 Edge 的顺序 Workflow，Worker 每次只推进当前未完成 Node，并按 Definition 顺序生成下一 Frontier，避免一次 Claim 再次执行完整 Workflow。

### 8.2 Checkpoint Fact Binding

单 Node Frontier 成功后，Worker 从同一事务中的 `WorkflowNodeExecution` 读取最近 attempt/status/output，并将其绑定到 Node-level Checkpoint。Multi-frontier 则使用 merged state 创建 Execution-level Checkpoint，避免错误地把多个 Branch 合并成单个 Node fact。

### 锁顺序约束

Worker Claim 与 Progression 固定采用 Frontier → Execution 的锁顺序，避免形成反向锁等待链。

### 当前边界

Persistence 层不重新执行 DAG 条件求值、State Merge 或 Planner；确定性 Next Frontier 必须由 Planner 输出。Durable Worker 是现有 Runtime 的调度适配层，不得复制第二套 Runtime。

## 9. 当前主线

```text
Durable Frontier Scheduling
   ├── Scheduler → Frontier enqueue        ✅
   ├── Frontier → Worker claim             ✅
   ├── Worker → Runtime bridge             ✅
   ├── Frontier lease heartbeat            ✅
   ├── Retry scheduling                    ✅
   ├── Runtime failure convergence         ✅
   ├── Frontier → Checkpoint progression  ✅
   ├── Next Frontier idempotent enqueue    ✅
   ├── Runtime/Planner progression wiring  ✅
   └── Unified success persistence path    ✅ 本轮
```

下一交付单元进入 Durable Execution 的 Recovery / Replay Closure：统一 Checkpoint resume、Frontier recovery、fencing generation 与 replay identity，并继续向 Scheduler、Worker、Runtime 的最终主线收敛。

## 10. 测试边界

当前只保留 Unit Test Contract；本环境未实际执行 pytest，因此不得记录 Unit Test PASS。Real API 后续必须实际验证 PostgreSQL 持久化以及 Scheduler → Frontier → Worker → Runtime → Retry → Checkpoint → Next Frontier 生命周期。