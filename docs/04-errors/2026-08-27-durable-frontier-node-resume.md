# Durable Frontier 已完成 Node Resume 闭环

日期：2026-08-27

## 问题

Durable Frontier 在 Worker Retry / Lease Recovery 后已经可以重新进入统一 Runtime Entry，但如果 Workflow 是线性节点列表，`WorkflowRuntime` 原有顺序执行入口会从节点列表头部重新遍历，存在重复执行已经成功持久化 `completed` Node 的风险。

## 根因

DAG Workflow 已经通过 `WorkflowDagResumePlanner` 根据 durable Node facts 计算 frontier；但无 `edges` 的线性 Workflow 不经过 DAG Planner，Runtime 仍直接遍历完整 `nodes`。

## 修复

新增 `DurableResumeWorkflowRuntime` 作为轻量 Resume Adapter：

1. 仅在无 DAG `edges` 的线性 Workflow 中读取当前 Execution 的 `WorkflowNodeExecution(status=completed)` durable facts；
2. 从 Runtime definition 中过滤已经成功完成的 Node；
3. 保留未完成 Node 的原始顺序；
4. DAG Workflow 不做过滤，继续唯一委托现有 Planner / Executor；
5. 不复制 Node Runtime、Retry、Checkpoint 或 Execution 状态机。

Runtime Entry 继续使用统一 `WorkflowRuntime` 作为实际执行器，只通过 adapter 准备 Resume definition。

## 不变量

```text
completed Node fact
    ↓
Retry / Lease Recovery
    ↓
过滤已完成 Node
    ↓
只执行未完成 Node
    ↓
Node Checkpoint
    ↓
Frontier / Execution progression
```

旧 Worker fencing、LeaseGuard、Checkpoint generation 与 DAG Planner Contract 均保持不变。

## 测试策略

新增 Unit Test 覆盖：

- 线性 Workflow 过滤已完成 Node；
- DAG Workflow 保持原 definition 并继续交给 Planner；
- 新鲜线性 Execution 不过滤任何 Node。

当前按项目开发策略暂停完整测试流程；Unit Test 仅实现，未在当前环境执行 pytest，不记录 PASS。
