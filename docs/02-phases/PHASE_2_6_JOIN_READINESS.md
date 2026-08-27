# Phase 2.6 Join Readiness / Execution / Runtime Integration

> 状态：**开发中**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

Join 已从独立 Readiness / Execution Contract 推进到真实 `WorkflowRuntime` Resume 路径，并完成 Recovery telemetry 统一出口以及 Automatic Recovery trace 生命周期接入。

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

Recovery、Scheduler、Automatic Recovery 与后续 Worker/Runtime 接入统一使用：

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

### Automatic Recovery 当前接入

`WorkflowExecutionAutomaticRecoveryService.recover()` 已使用同一 `WorkflowRecoveryTelemetry` 完成：

```text
start_trace(execution_id)
        ↓
evaluate / resume
        ↓
RECOVERY_ATTEMPT(trace_id)
        ↓
finish_trace(trace_id)
```

成功与拒绝两条路径都必须关闭 trace；`RECOVERY_ATTEMPT` 与 `RECOVERY_TRACE_FINISHED` 使用相同 `trace_id`，并携带 `phase=automatic_recovery`。duration 使用服务内 monotonic clock 计算，不把业务时间字段作为耗时来源。

当前保留 `event_logger` 构造参数兼容既有调用方，但新代码统一经 `WorkflowRecoveryTelemetry` 出口发射事件；未引入第二套 exporter。

## Unit Test

新增 / 覆盖：

```text
backend/tests/unit/test_workflow_dag_runtime_join.py
backend/tests/unit/test_workflow_recovery_observability.py
backend/tests/unit/test_workflow_automatic_recovery_telemetry.py
```

新增 Automatic Recovery telemetry 测试：

- 成功恢复产生 start → attempt → finish；
- 三个事件使用同一 `trace_id`；
- Resume Execution ID 在 attempt / finish 中保持关联；
- duration 在 attempt / finish 中一致；
- 拒绝恢复同样必须关闭 trace；
- reason_code / outcome 正确传递。

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

Recovery telemetry 已进一步从“事件出口 Contract”推进到 Automatic Recovery 实际调用链。

当前进入最终收口阶段：

1. Worker / Recovery Scheduler / Runtime 统一接入 `WorkflowRecoveryTelemetry`，建立 Recovery → Resume → Runtime trace continuity；
2. Worker claim / lease / fencing 与 Automatic Recovery 的持久化闭环；
3. Real API + PostgreSQL + 独立 Worker 验证入口，但不作为当前主线阻塞项；
4. Phase 2.6 Closure；
5. Closure 后进入下一阶段企业级执行能力。
