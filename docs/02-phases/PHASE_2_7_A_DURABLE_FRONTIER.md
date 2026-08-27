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
- `transition_owned_frontier()` 同时校验 `worker_owner + attempt` fencing generation，阻止 stale Worker 覆盖新 Worker。

## 6. 本轮交付边界

本轮新增 `enqueue_frontier()` 与 Unit Test Contract，使 Durable Frontier 具备正式幂等入队入口；当前尚未把现有 Scheduled Trigger Runtime 改造成“Frontier-only dispatch”，因为现有 Worker 仍以 `WorkflowExecution` 为正式消费单元。直接切换会产生未消费 Frontier 或重复执行风险。

因此下一交付单元必须先完成：

```text
Scheduler
   ↓
Durable Frontier enqueue
   ↓
Worker Frontier Claim
   ↓
Execution ownership / fencing
   ↓
唯一 Workflow Runtime
```

接入时必须复用现有 `WorkflowExecutionService`、Worker ownership 与 Runtime，不得创建第二套执行路径。

## 7. 测试边界

当前只保留 Unit Test Contract；本环境未实际执行 pytest，因此不得记录 Unit Test PASS。Real API 后续必须实际验证 PostgreSQL 持久化以及 Scheduler → Frontier → Worker → Runtime 生命周期。