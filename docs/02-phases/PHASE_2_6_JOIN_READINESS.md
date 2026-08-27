# Phase 2.6 Join Readiness / Execution Contract

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

Join 已从单纯 Readiness Contract 推进为独立 Execution Contract。

正式入口：

```text
WorkflowDagJoinReadiness
WorkflowDagJoinReadinessService
WorkflowDagJoinExecutionResult
WorkflowDagJoinExecutor
```

新增：

```text
backend/app/services/workflow/checkpoint/recovery/dag_join_executor.py
backend/tests/unit/test_workflow_dag_join_executor.py
```

## Join Execution Contract

```text
Join Readiness
      ↓
WorkflowDagJoinExecutor
      ↓
execute Join Node
      ↓
validate object output
      ↓
persister callback
      ↓
Join execution result
```

Executor 不直接操作数据库。`persister(node_id, state)` 必须由 `WorkflowExecutionService` 在现有 Worker ownership、fencing 和事务边界内提供，并负责 Join NodeExecution + Checkpoint。

如果调用方已经从持久化 `WorkflowNodeExecution` 验证 Join 为 `completed`，传入 `already_completed=True`，Executor 禁止再次调用 Node。

## Join → Next Frontier

只有以下条件同时成立才允许 downstream Node 进入 next frontier：

```text
all predecessor completed
AND predecessor outputs available
AND state merge successful
AND Join Node completed + checkpointed
```

禁止仅凭 `join_ready=True` 推进 downstream。

## Runtime 接入边界

目标闭环：

```text
WorkflowRuntime
      ↓
WorkflowDagJoinReadinessService
      ↓
WorkflowDagJoinExecutor
      ↓
transition_node(join, running)
      ↓
execute Join
      ↓
transition_node(join, completed)
      ↓
NodeExecution + Checkpoint
      ↓
重新读取 completed facts
      ↓
DAG Planner
      ↓
next frontier
```

本轮完成 Join Execution Domain Contract；下一轮直接接入真实 Runtime Join path，不新增第二套状态持久化机制。

## Unit Test

新增测试覆盖：

- ready Join 正常执行并调用 persistence boundary；
- not-ready Join 拒绝；
- 已完成 Join 不重复执行；
- Node identity mismatch 拒绝；
- 非对象 output 拒绝。

当前策略：完整 Backend Regression、Real API、E2E、Release Gate 暂停；只维护 Unit Test。**本轮没有实际执行测试，因此不能记录为 Unit Test PASS。**

## 下一主线

1. 将 `WorkflowDagJoinExecutor` 接入 `WorkflowRuntime`；
2. 复用 `transition_node()` 完成 Join running/completed + Checkpoint；
3. 从持久化 NodeExecution 判断 Join 已完成，避免 Resume 重复执行；
4. Join completed 后重新计算 downstream frontier；
5. 接入 Recovery observability；
6. Phase 2.6 Closure。
