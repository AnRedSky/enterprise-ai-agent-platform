# Phase 2.6 Runtime Trace Continuity

> 状态：**开发中 / 收口阶段**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

本轮将已经持久化的 Recovery Trace Link 正式延续到 `WorkflowRuntime`，并继续把 Scheduler Scan 接入统一 trace 生命周期：

```text
Scheduler Scan
      ↓
Automatic Recovery / Scheduled Dispatch
      ↓
Resume Execution
      ↓
Recovery Trace Link
      ↓
Worker
      ↓
WorkflowRuntime
```

Runtime 不创建第二个 Recovery trace，也不从 Trace Event 读取业务 payload。Worker 创建的 Resume Execution 进入 Runtime 后，只通过 `WorkflowRecoveryTraceLinkService.get_trace_id()` 恢复已有 `trace_id`，随后通过统一 `WorkflowRecoveryTelemetry` 发出 Runtime started / finished 控制面事件。

Scheduler Runtime 通过 package-level `ScheduledTriggerScheduler` 入口使用 `TracedScheduledTriggerScheduler`，在 `tick_once()` 外围建立 scan trace 生命周期。原有 `runtime.py` 调度领域实现保持不变，避免复制 Scheduler 状态机。

## Scheduler Trace 生命周期

```text
WorkflowSchedulerTraceService.start_scan()
        ↓
ScheduledTriggerScheduler.tick_once()
        ↓
Lease / Slot / Dispatch / Misfire
        ↓
WorkflowSchedulerTraceService.finish_scan()
```

同一轮 Scheduler Scan 的 `started / scan.completed / finished` 事件共享同一个 `trace_id`。正常扫描以 `completed` 收口；异常扫描以 `failed` 收口，并继续向上抛出原始异常。

Scheduler Trace 只携带调度控制面字段，不写入业务 `input_data`，因此不会通过 Scheduled Trigger 的业务状态传递 trace identity，也不会扩大敏感数据边界。

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

## Trace 生命周期

Recovery Resume Runtime 使用同一 `trace_id`：

```text
Scheduler Scan
        ↓
RECOVERY_WORKER_STARTED
        ↓
workflow.recovery.runtime.started
        ↓
WorkflowRuntime / DAG / Join / Checkpoint
        ↓
workflow.recovery.runtime.finished
        ↓
RECOVERY_WORKER_FINISHED
```

Runtime 事件只记录：

- `execution_id`
- `resume_execution_id`
- `trace_id`
- `phase`
- `outcome`
- `reason_code`
- `duration_ms`

禁止记录 Checkpoint `state_data`、Prompt、Secret、Provider credential 或完整业务 payload。

## Unit Test

新增：

```text
backend/tests/unit/test_workflow_scheduler_runtime_trace.py
```

覆盖：

1. package-level trace-aware Scheduler Runtime 入口；
2. `tick_once()` 正常完成时 started / completed / finished 共享同一 `trace_id`；
3. Scheduler Runtime 异常时仍然 finish trace 并标记 `failed`；
4. 原始 Scheduler 异常继续向调用方传播。

既有：

```text
backend/tests/unit/test_workflow_scheduler_trace.py
backend/tests/unit/test_workflow_dag_runtime_join.py
```

继续覆盖 Scheduler Trace Contract 与 Runtime / Join Trace Continuity。

当前仅保留 Unit Test 验证范围。Backend Full Regression、Real API、E2E、Release Gate 暂停；**未实际执行的测试不得记录 PASS**。

## 下一主线

```text
Scheduler Scan
      ↓
Automatic Recovery
      ↓
Resume Trace Link
      ↓
Worker Trace
      ↓
Runtime Trace
      ↓
DAG Branch
      ↓
Join
      ↓
Checkpoint
      ↓
Execution Completed
```

下一步继续完成 Scheduler → Recovery → Worker → Runtime 的同一 Trace lineage 实际传递，并随后进入 Phase 2.6 Closure；不再新增平行 Trace 抽象。
