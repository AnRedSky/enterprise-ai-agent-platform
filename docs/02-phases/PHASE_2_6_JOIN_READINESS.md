# Phase 2.6 Join Readiness / Execution / Runtime Integration

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

Join 已从独立 Readiness / Execution Contract 推进到真实 `WorkflowRuntime` Resume 路径，并完成 Recovery telemetry 的统一出口边界。

正式入口：

```text
WorkflowDagJoinReadiness
WorkflowDagJoinReadinessService
WorkflowDagJoinExecutionResult
WorkflowDagJoinExecutor
WorkflowRuntime (DAG Join extension)
WorkflowRecoveryTelemetry
```

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
WorkflowRuntime DAG Join extension
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

Join Node 是纯状态汇聚节点，不调用 Model Provider；其执行输出是输入 state 的独立副本。Runtime 复用基础 Runtime 的 Retry / Timeout / NodeExecution / Checkpoint 路径，而不是复制一套 Join persistence。

## State Source 安全边界

Join 的输入不信任 Resume Execution 初始 `input_data` 中可能存在的旧状态。

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

同一 Join Node 的多个 predecessor 继续通过 `WorkflowDagBranchStateMergeService` 合并；同键不同值显式拒绝，禁止 last-write-wins。

## Join Idempotency

Join Node 使用现有 `(execution_id, node_id)` NodeExecution 唯一事实及 Worker ownership / fencing。

当 Join 已经持久化为 completed 时，Resume frontier 不会再次把 Join 作为未完成 frontier 执行，而是重新读取 completed facts 并继续计算 downstream frontier。

本轮没有新增 Join 专用数据库表，也没有在 Join Runtime 扩展中直接提交数据库事务。

## Recovery Observability / Trace Contract

Recovery、Scheduler 和后续 Worker/Runtime 接入统一使用：

```text
WorkflowRecoveryEvent
        ↓
WorkflowRecoveryTelemetry
   ┌────┼────┐
   ↓    ↓    ↓
 Logger Trace Metrics
```

`WorkflowRecoveryTelemetry` 是 Domain 与具体 OpenTelemetry / Prometheus / 云厂商 SDK 之间的隔离边界：

- Logger 始终输出结构化事件；
- Trace 通过可选 `trace_sink` 注入；
- Metrics 通过可选 `metrics_sink` 注入；
- 三者接收完全相同的 `WorkflowRecoveryEvent`，避免 Recovery 事件在不同出口产生不同字段定义；
- `trace_id` / `span_id` / `parent_span_id` / `phase` / `duration_ms` 已进入稳定事件模型；
- telemetry 层不得携带 `state_data`、Secret 或其他敏感 Checkpoint 内容。

Trace 生命周期统一为：

```text
start_trace()
    ↓
RECOVERY_TRACE_STARTED
    ↓
RECOVERY_ATTEMPT / scan events
    ↓
finish_trace()
    ↓
RECOVERY_TRACE_FINISHED
```

当前仍不在 Recovery Domain 内直接依赖具体 Trace/Metrics SDK，后续 Worker 与 Automatic Recovery 接入时复用该 facade。

## Unit Test

覆盖：

```text
backend/tests/unit/test_workflow_dag_runtime_join.py
backend/tests/unit/test_workflow_recovery_observability.py
```

新增 telemetry 测试：

- 相同 Recovery Event 同时 fan-out 到 Trace / Metrics sink；
- Trace start / finish 使用同一 `trace_id`；
- duration / outcome / reason_code 正确传递；
- 事件序列化继续排除 `state_data` / Secret。

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

当前进入收口阶段：

1. Recovery / Worker / Runtime 统一接入 `WorkflowRecoveryTelemetry`；
2. Worker 自动恢复与真实 PostgreSQL / API 集成验证；
3. Phase 2.6 Closure；
4. Closure 后进入下一阶段主线能力。
