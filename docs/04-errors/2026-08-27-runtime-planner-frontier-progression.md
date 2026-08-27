# 2026-08-27 Runtime / Planner Durable Frontier Progression

## 问题

Durable Frontier 已完成持久化、Claim、Fencing、Retry 与基础 Checkpoint Progression，但默认 Worker 之前仍通过完整 Workflow Runtime 一次性执行整个 Workflow，导致 Durable Frontier 无法真正成为每次调度的执行边界。

## 根因

现有 `WorkflowRuntime.execute()` 同时承担 HTTP/兼容入口的完整 Workflow 执行循环；直接替换该入口会改变已有手动执行语义，并可能形成第二套 Runtime 调度规则。

## 处理

新增 `PlannerDrivenDurableFrontierWorkflowWorker` 作为默认 Worker 入口。该适配器继承既有 `DurableFrontierWorkflowWorker`，复用唯一 `WorkflowRuntime` 的 Planner、Node Retry、Multi-frontier Executor 与 Checkpoint 能力。

一次 Durable dispatch 现在执行：

```text
Frontier Claim
  ↓
Execution ownership
  ↓
Planner current frontier
  ↓
Node / Multi-frontier execution
  ↓
Checkpoint facts
  ↓
Planner rebuild
  ↓
Current Frontier completed
  ↓
Next Frontier idempotent enqueue
```

## 并发与一致性约束

- Frontier terminal transition 继续校验 `worker_owner + attempt`；
- Next Frontier 使用 `WorkflowFrontierIdentity` 幂等；
- 同一 Execution / Workflow Version 才允许创建后继 Frontier；
- Worker Claim 与 Progression 保持 Frontier → Execution 锁顺序；
- 历史 Scheduled Trigger 首个 Frontier 可能保存完整 Node 集合，首次 dispatch 仅将其作为 bootstrap work item，并按 Planner root 实际执行；后续 Frontier 必须严格与 Planner 输出一致；
- 无 Edge 顺序 Workflow 每次只推进一个未完成 Node，避免一次 Claim 再次执行完整 Workflow；
- 未实际执行 pytest，因此不记录 Unit Test PASS。

## 后续

下一主线统一 Runtime retryable failure、Frontier retry scheduling、expired lease recovery 与 terminal failure，确保异常路径同样只产生一个 Durable Work Item。