# 2026-08-27 Durable Resume Frontier Bootstrap

## 问题

此前 Durable Resume 已能基于失败 Execution 的最新 `node.completed` Checkpoint 创建新的 pending `WorkflowExecution`，但 Resume 创建边界没有同时建立新的 Durable Frontier，也没有把 Source Execution 的 completed Node facts 复制到 Resume Execution。

这会产生两个实际风险：

1. Resume Execution 已持久化，但没有 Frontier，默认 Frontier Worker 无法消费该 Resume；
2. Resume Execution 的 Planner 看不到 Source 已完成 Node，可能从 DAG root 重新执行已经完成的节点。

## 根因

`WorkflowExecutionService.resume_from_latest_checkpoint()` 原本只负责创建 Resume Execution。Scheduled Trigger 的首个 Frontier 创建位于 Trigger Domain，不能直接复用到 Recovery Domain，否则会让 Recovery 依赖 Scheduled Trigger Contract。

## 修复

新增 `WorkflowExecutionResumeBootstrapService`：

```text
Source failed Execution
        ↓
completed Node facts
        ↓
复制到 Resume Execution
        ↓
WorkflowDagResumePlanner
        ↓
首个 Frontier Identity
        ↓
enqueue_frontier()
```

`WorkflowExecutionResumeContractService` 现在：

```text
Source row lock
      ↓
Resume idempotency check
      ↓
resume_from_latest_checkpoint(commit=False)
      ↓
Resume Node lineage bootstrap
      ↓
首个 Durable Frontier enqueue
      ↓
COMMIT
```

因此不存在“Resume Execution 已创建但 Frontier 尚未创建”的中间提交状态。

## 设计边界

- Source Workflow Version 固定，不允许 Resume 隐式漂移版本；
- Resume 使用 `resume:<source_execution_id>:checkpoint:<sequence>` 确定性幂等键；
- DAG Resume 继续复用唯一 `WorkflowDagResumePlanner`；
- 无 Edge Workflow 按 Definition 顺序选择首个未完成 Node；
- Source completed Node facts 复制到 Resume Execution 后，Worker 不会从 root 重复执行；
- Resume Frontier 使用新的 Resume Execution identity，不复用 Source Frontier key；
- Bootstrap 不启动 Runtime、不执行 Node、不独立 commit；
- 相同 Resume idempotency key 命中时返回已有 Resume，不重复创建 Frontier。

## 验证范围

新增/更新 Unit Test Contract，覆盖：

- Resume idempotency hit 不创建新 Resume；
- lineage drift 拒绝；
- 非确定性 Resume key 拒绝；
- Resume 创建使用 `commit=False`；
- Bootstrap 完成后才执行一次外层 commit。

当前环境未实际执行 pytest，因此不记录 Unit Test PASS。