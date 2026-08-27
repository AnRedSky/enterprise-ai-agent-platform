# Phase 2.6 Runtime Trace Continuity

> 状态：**开发中 / 收口阶段**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

本轮将已经持久化的 Recovery Trace Link 正式延续到 `WorkflowRuntime`，补齐：

```text
Automatic Recovery
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

更新：

```text
backend/tests/unit/test_workflow_dag_runtime_join.py
```

覆盖：

1. Join Node Definition 校验；
2. Join 纯状态汇聚；
3. Join 从持久化 predecessor output 重建 state；
4. stale Resume input 不覆盖持久化 predecessor state；
5. Runtime 从 Recovery Trace Link 恢复 `trace_id`；
6. Runtime started / finished 使用同一 `trace_id`。

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

下一步继续收口 Scheduler → Automatic Recovery → Worker → Runtime 的同一 Trace lineage，并最终完成 Phase 2.6 Closure。
