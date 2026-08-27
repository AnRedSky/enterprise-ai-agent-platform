# Scheduler → Durable Frontier → Worker Bridge

日期：2026-08-27

## 本轮问题

此前 Scheduled Trigger 已经可以创建 pending `WorkflowExecution`，但 Durable Frontier 虽已具备 PostgreSQL persistence、claim、lease fencing 与 recovery，却没有进入正式 Scheduler/Worker 消费链路。

这会产生两套事实来源：Scheduler 产生 Execution work item，而 Frontier 只是旁路记录。若直接让 Worker 改成 Frontier-only，会导致已有 Scheduled Execution 无法被消费；若同时保留两套消费，则可能出现重复 Runtime。

## 处理

建立单一桥接：

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

## 关键约束

1. Scheduled Trigger 使用同一个 slot idempotency key，创建 Execution 后立即创建首个 Frontier；重复 slot 不创建第二个 Frontier。
2. Frontier Claim 与对应 pending Execution ownership 在同一事务中完成；无法取得 Execution ownership 时整体 rollback，避免孤儿 claimed Frontier。
3. Worker 仍复用既有 `LeaseAwareWorkflowWorker`，不复制 Runtime、Retry、Checkpoint 或 Recovery 状态机。
4. Frontier lease heartbeat 使用 `worker_owner + attempt` fencing；旧 Worker 不能刷新或完成新 Worker 已重新 Claim 的 Frontier。
5. Execution terminal 后才允许 Frontier 进入 completed/failed；如果 Worker 因 lease loss 中止，Frontier 不伪造 terminal state，等待 lease recovery。
6. Manual/Webhook 入口的 Execution 模型保持独立，后续可按相同 Durable Work Item Contract 扩展，不在本轮强行改变公开触发语义。

## 测试状态

已新增 Unit Test Contract，覆盖 Scheduled Trigger enqueue、默认 Worker Frontier dispatch、同事务 ownership 与 fencing heartbeat。当前环境没有实际执行 pytest，因此不得标记 Unit Test PASS。