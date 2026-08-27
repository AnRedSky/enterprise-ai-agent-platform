# Durable Frontier Retry Budget Resume

## 问题

Worker Lease Recovery 会重新进入 Runtime Resume，但原有 Node Retry 与 Workflow Retry 计数只存在于当前 Runtime 的内存变量中。Worker 崩溃后重新创建 Runtime 会把计数器清零，从而可能超过 Workflow Definition 中声明的 Retry 上限。

## 根因

`WorkflowNodeExecution.attempt` 已经是持久化事实，但 Runtime 原先每次进入 `_execute_node_with_policy()` 都从 `attempt = 0` 开始；同时 `workflow_retry_counter` 每次 Runtime Resume 都重新初始化为 0。

因此：

```text
Worker A
  ↓
Node B attempt = 2
  ↓
Worker Lease Lost
  ↓
Recovery
  ↓
Worker B
  ↓
Runtime retry counter = 0
  ↓
可能绕过原 Retry budget
```

## 修复

`DurableResumeWorkflowRuntime` 现在：

1. 读取当前 Execution 的持久化 `WorkflowNodeExecution.attempt`；
2. 对 `failed` Node 将剩余 Node Retry 次数转换为本次 Runtime 的局部上限；
3. 已达到 `retry.max_attempts` 的 Node 不再重新执行；
4. 根据所有 Node 的 `attempt - 1` 恢复已消耗的 Workflow Retry budget；
5. DAG Planner、Node Runtime、Checkpoint 算法继续复用既有正式实现。

## 不变量

```text
Node attempt = 持久化 Retry 事实
Workflow retry budget = 跨 Worker Resume 仍然有效
Worker fencing generation = 独立于 Retry budget
```

Retry budget 恢复不能修改 Worker fencing，也不能通过数据库状态回退绕过 Execution 状态机。

## 验证范围

本轮仅实现 Unit Test，不执行完整测试流程。pytest 未执行，因此不得记录为 PASS。
