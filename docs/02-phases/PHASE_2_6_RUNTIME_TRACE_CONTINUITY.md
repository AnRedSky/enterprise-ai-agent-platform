# Phase 2.6 Runtime Trace Continuity

> 状态：**开发中 / 收口阶段**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

本轮完成 Scheduler Recovery Scan → Automatic Recovery 的实际 trace lineage 传递。Scheduler 为一次 Recovery Scan 建立父级 `trace_id`，每个 Automatic Recovery 创建自己的 Recovery `trace_id`，并通过 `parent_trace_id` 保留父子关联：

```text
Scheduler Scan trace = S
        ↓
Automatic Recovery trace = R
        │
        ├── parent_trace_id = S
        ↓
Resume Execution
        ↓
Recovery Trace Link
        ↓
Worker trace = R
        ↓
WorkflowRuntime trace = R
```

这样避免把一个 Scan trace 错误地复用成多个 Recovery trace，同时又可以从 Recovery 事件重建 Scheduler → Recovery 的父子关系。

## Scheduler Recovery Trace 生命周期

```text
WorkflowRecoveryScheduler.scan_once()
        ↓
WorkflowSchedulerTraceService.start_scan()
        ↓
failed Execution candidates
        ↓
WorkflowExecutionAutomaticRecoveryService.recover(
    parent_trace_id=scheduler_trace_id
)
        ↓
Automatic Recovery child trace
        ↓
Resume + durable Recovery Trace Link
        ↓
WorkflowSchedulerTraceService.finish_scan()
```

Scheduler Scan 的 `started / scan.completed / finished` 事件继续共享父级 `trace_id`。每个 Automatic Recovery 使用独立 child `trace_id`，并在 `workflow.recovery.trace.*` 与 `workflow.recovery.attempt` 事件中携带 `parent_trace_id`。

## Trace Contract

`WorkflowRecoveryEvent` 新增：

- `parent_trace_id`：标识当前 Recovery trace 的父级 Scheduler trace；
- `trace_id`：当前事件所属的 Recovery / Scheduler trace；
- `execution_id` / `resume_execution_id`：执行身份关联。

该字段只用于控制面 lineage，不承载业务 state。

## Runtime 边界

```text
WorkflowRuntime
├── Join Node
│   └── 只执行已由 Join Readiness Contract 验证的 merged state
│
└── Recovery Trace Continuity
    ├── 读取持久化 trace identity
    ├── 不读取 trace data payload
    ├── 不修改 Resume input_data
    └── 不新增 Trace / Checkpoint 数据表
```

Join 继续复用基础 Runtime 的 Retry、Timeout、CircuitBreaker、NodeExecution 与 Checkpoint 事务边界；Join 不调用 Model Provider。

## 当前完整链路

```text
Scheduler Scan
    │
    │ trace_id = S
    ↓
Automatic Recovery
    │
    │ trace_id = R
    │ parent_trace_id = S
    ↓
Resume Execution
    │
    ↓
Persistent Recovery Trace Link
    │
    │ trace_id = R
    ↓
Worker
    │
    │ trace_id = R
    ↓
WorkflowRuntime
    │
    ↓
DAG Branch
    │
    ↓
Join
    │
    ↓
Checkpoint
    │
    ↓
Execution Completed
```

Runtime / Worker 继续使用 Resume Execution 持久化的 Recovery child `trace_id`；Scheduler parent trace 不写入业务 `input_data`。

## Unit Test

更新：

```text
backend/tests/unit/test_workflow_recovery_scheduler.py
backend/tests/unit/test_workflow_recovery_observability.py
```

覆盖：

1. Recovery Scheduler 创建 Scan Trace；
2. 每个 Automatic Recovery 收到相同的 Scheduler `parent_trace_id`；
3. Scheduler Scan 统计仍通过统一 Trace Service 收口；
4. `WorkflowRecoveryEvent` 正确序列化 `parent_trace_id`；
5. Trace lifecycle 保持 child `trace_id` 稳定；
6. 敏感数据边界不因 lineage 字段扩大。

当前仅保留 Unit Test 验证范围。Backend Full Regression、Real API、E2E、Release Gate 暂停；**未实际执行的测试不得记录 PASS**。

## 下一主线

```text
Scheduler parent trace
        ↓
Automatic Recovery child trace
        ↓
Resume Trace Link
        ↓
Worker / Runtime child trace
        ↓
Claim / Lease / Fencing
        ↓
Checkpoint durable facts
        ↓
Phase 2.6 Closure
```

下一步不再新增 Trace 抽象，直接完成 Worker claim / lease / fencing 与 Recovery Resume 的最终持久化闭环，并验证 stale worker / lease loss 不会错误完成 Recovery Execution。
