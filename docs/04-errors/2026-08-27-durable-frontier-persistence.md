# Durable Frontier Persistence

## 本轮问题

此前 `WorkflowFrontierIdentity` 只有内存领域契约，Scheduler/Worker 没有独立的 Durable work item 表，因此 Frontier 在进程重启、并发 Worker 和租约恢复场景下无法成为稳定的持久化调度边界。

## 实施

本轮新增 `WorkflowFrontier` SQLAlchemy 模型与 Alembic `0035_workflow_frontier` migration，并建立：

- tenant + frontier_key 唯一约束；
- tenant/status/available_at claim 索引；
- execution 查询索引；
- worker lease 查询索引；
- `claim_next_frontier()` 的 tenant-scoped `FOR UPDATE SKIP LOCKED` claim；
- repository 不负责 commit，由 Scheduler/Worker caller 保持事务所有权；
- stale Worker 不得释放其它 Worker 的 lease。

## 当前边界

```text
Planner
  ↓
WorkflowFrontierIdentity
  ↓
WorkflowFrontier durable row
  ↓
claim_next_frontier()
  ↓
Worker lease
```

本轮只完成 Durable persistence + claim 基础能力。Lease fencing、过期 lease recovery、Scheduler/Worker 正式接入及 Frontier → Checkpoint progression 尚未标记完成。

## 验证策略

Unit Test 已新增，覆盖 claim 使用 `SKIP LOCKED`、tenant-scoped queue、caller-owned transaction 和 stale ownership rejection。当前环境未执行 pytest，因此不得标记 Unit Test PASS。
