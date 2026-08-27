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

## 7. 下一交付单元

当前剩余主线：

```text
Durable Frontier Scheduling
   ├── Scheduler → Frontier enqueue       ✅
   ├── Frontier → Worker claim             ✅
   ├── Worker → Runtime bridge             ✅
   ├── Frontier lease heartbeat             ✅
   ├── Retry scheduling                     ⏭
   └── Frontier → Checkpoint progression    ⏭
```

下一步直接实现 Frontier Retry Scheduling：把可重试 Runtime failure 映射到 `retry_wait + available_at`，并保证 retry 与 fencing generation、Execution terminal state 不发生重复执行。

## 8. 测试边界

当前只保留 Unit Test Contract；本环境未实际执行 pytest，因此不得记录 Unit Test PASS。Real API 后续必须实际验证 PostgreSQL 持久化以及 Scheduler → Frontier → Worker → Runtime 生命周期。