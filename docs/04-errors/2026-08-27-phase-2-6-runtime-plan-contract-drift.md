# Phase 2.6：Runtime Plan Contract 漂移

## 1. 发现时间

2026-08-27

## 2. 问题

DAG Resume Runtime Plan 已从单 frontier 结构升级为：

```text
completed_node_ids
frontier_node_ids
nodes
state_data
```

但旧的 `WorkflowDagResumeRuntimeSequencePlanner` 仍按旧字段：

```text
frontier_node_id
node
```

构造 `WorkflowDagResumeRuntimePlan`。

这会导致 Runtime Resume 路径在真正执行前发生 Contract 不一致，并且如果简单通过把多个 frontier 压成顺序 Node，会把多个 Branch 错误地共享同一份 state，破坏 Branch state isolation。

## 3. 根因

此前 Multi-frontier Planner / Executor 的 Contract 已经向前演进，但旧的顺序兼容规划器没有在同一交付单元内同步迁移。

## 4. 修复

`dag_runtime_sequence.py` 已同步到新版 `WorkflowDagResumeRuntimePlan`：

- 单 frontier 使用 `frontier_node_ids=(node_id,)`；
- 单 frontier 使用 `nodes=(node,)`；
- 继续只承担顺序 Runtime 的单 frontier 规划；
- 发现多个 frontier 时明确拒绝，并要求进入 `WorkflowDagMultiFrontierExecutor`；
- 不通过共享 merged state 把多个 Branch 强行线性化。

## 5. 为什么不能直接兼容多个 frontier

多个 Branch 必须分别执行并分别维护状态与 Checkpoint。若顺序规划器把：

```text
A + B
```

直接变成：

```text
A → B
```

并让 B 消费 A 的 state，则 DAG 的并行 Branch 语义会被改变；如果让 A/B 都消费 merged state，则会产生跨 Branch 状态污染。

因此正确边界是：

```text
单 frontier → Sequence Planner
多 frontier → Multi-frontier Executor
```

## 6. 防止再次发生

后续修改 `WorkflowDagResumeRuntimePlan` 时，必须同步检索并更新：

```text
WorkflowDagResumeRuntimeSequencePlanner
WorkflowDagMultiFrontierExecutor
WorkflowRuntime
WorkflowExecutionService
相关 Unit Test
Phase / Acceptance 文档
```

Contract 字段变更不得只修改生产定义而遗漏消费者。

## 7. 当前状态

代码修复已提交 `main`。本轮未执行完整测试流程；测试结果仅允许记录实际执行结果。