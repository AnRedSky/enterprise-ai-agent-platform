# Phase 2.6 Join Readiness / Execution / Runtime Integration

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

Join 已从独立 Readiness / Execution Contract 推进到真实 `WorkflowRuntime` Resume 路径。

正式入口：

```text
WorkflowDagJoinReadiness
WorkflowDagJoinReadinessService
WorkflowDagJoinExecutionResult
WorkflowDagJoinExecutor
WorkflowRuntime (DAG Join extension)
```

新增 Runtime 扩展：

```text
backend/app/runtime/workflow/dag_runtime.py
```

公共入口 `backend/app/runtime/workflow/__init__.py` 已改为暴露 DAG Join-aware `WorkflowRuntime`；基础 Runtime 的 Retry、Timeout、CircuitBreaker、NodeExecution 与 Checkpoint 逻辑仍由原 `runtime.py` 提供。

## Runtime Join Contract

Resume 当前 frontier 为 Join 时：

```text
Persisted completed NodeExecution
        ↓
predecessor output_data
        ↓
WorkflowDagJoinReadinessService
        ↓
all predecessors completed + state merge succeeds
        ↓
WorkflowRuntime
        ↓
_execute_node_with_policy()
        ↓
execute_node(join)
        ↓
transition_node(join, completed)
        ↓
NodeExecution + Checkpoint
        ↓
重新读取 completed facts
        ↓
DAG Resume Planner
        ↓
next frontier
```

Join Node 是纯状态汇聚节点，不调用 Model Provider；其执行输出是输入 state 的独立副本。这样 Join 不会引入第二套 Provider / Retry / Checkpoint 规则。

## State Source 安全边界

Join 的输入不再信任 Resume Execution 初始 `input_data` 中可能存在的旧状态。

真实 Resume 时：

```text
source execution / resume execution completed NodeExecution
        ↓
node.output_data
        ↓
predecessor mapping
        ↓
Join Readiness
        ↓
merged state
```

因此已经持久化的 predecessor output 是 Join 的权威输入事实。

同一 Join Node 的多个 predecessor 继续通过 `WorkflowDagBranchStateMergeService` 合并；同键不同值显式拒绝，禁止 last-write-wins。

## Join Idempotency

Join Node 仍然使用现有 `(execution_id, node_id)` NodeExecution 唯一事实及 Worker ownership / fencing。

当 Join 已经持久化为 completed 时，Resume frontier 不会再次把 Join 作为未完成 frontier 执行，而是重新读取 completed facts 并继续计算 downstream frontier。

本轮没有新增 Join 专用数据库表，也没有在 Join Runtime 扩展中直接提交数据库事务。

## Unit Test

新增：

```text
backend/tests/unit/test_workflow_dag_runtime_join.py
```

覆盖：

- `join` Node Definition 可被 Runtime 接受；
- Join Node 保持输入 state 的副本语义；
- Resume Join 使用持久化 predecessor output，而不是 stale Resume input；
- Join frontier state 正确构造。

完整 Backend Regression、Real API、E2E、Release Gate 继续暂停。**本轮未实际执行测试，因此不得记录 Unit Test PASS。**

## 当前结论

Phase 2.6 的核心 DAG Resume 链已经完成：

```text
Branch A / B
    ↓
NodeExecution + Checkpoint
    ↓
Join Readiness
    ↓
Join Runtime
    ↓
Join NodeExecution + Checkpoint
    ↓
Next Frontier
```

剩余工作已经从核心 DAG 执行转入收口任务：

1. Recovery observability / trace 统一接入；
2. Worker 自动恢复与真实 PostgreSQL / API 集成验证；
3. Phase 2.6 Closure；
4. Closure 后进入下一阶段主线能力。
