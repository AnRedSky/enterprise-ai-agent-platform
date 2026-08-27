# Phase 2.6 Join Readiness / Execution / Runtime Integration

> 状态：**开发中 / 收口阶段**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

Join 已从独立 Readiness / Execution Contract 推进到真实 `WorkflowRuntime` Resume 路径，并完成 Recovery telemetry 统一出口、Automatic Recovery trace 生命周期、Recovery → Resume trace lineage 持久化以及 Worker → Runtime trace continuity。

正式入口：

```text
WorkflowDagJoinReadiness
WorkflowDagJoinReadinessService
WorkflowDagJoinExecutionResult
WorkflowDagJoinExecutor
WorkflowRuntime (DAG Join extension)
WorkflowRecoveryTelemetry
WorkflowRecoveryTraceLinkService
```

## Recovery Trace Lineage

Automatic Recovery 成功创建或幂中 Resume Execution 后，会通过 `WorkflowRecoveryTraceLinkService` 在已有 `WorkflowTraceEvent` 中持久化：

```text
Recovery trace_id
      ↓
WorkflowTraceEvent(execution=resume)
      ↓
Resume Execution
      ↓
独立 Worker 读取 trace_id
```

Trace Link 只保存 `source_execution_id`、`resume_execution_id`、`trace_id`、`phase`，不复制 Checkpoint state，也不修改 `input_data`。

同一 Resume Execution + trace_id 重复建立 Link 时直接返回已有事件，保证 Automatic Recovery 重试不会产生重复 lineage。

## Worker Trace Continuity

Worker 接管 pending Resume Execution 后，通过 `WorkflowRecoveryTraceLinkService.get_trace_id()` 从持久化 `WorkflowTraceEvent` 恢复 Recovery trace identity；Worker 随后通过统一 `WorkflowRecoveryTelemetry` 发出：

```text
RECOVERY_WORKER_STARTED
        ↓
WorkflowExecutionService.run()
        ↓
DAG / Join / Checkpoint
        ↓
RECOVERY_WORKER_FINISHED
```

Worker 不读取 Trace Event 中的业务 payload，也不修改 Resume `input_data`。没有 Recovery lineage 的普通 pending Execution 不会被强制伪造 Recovery trace。

## Unit Test

新增：

```text
backend/tests/unit/test_workflow_recovery_trace_link.py
backend/tests/unit/test_workflow_recovery_worker_trace.py
```

覆盖 Trace Link 新建/幂等、trace identity 查询以及无 lineage 时的安全返回。

完整 Backend Regression、Real API、E2E、Release Gate 继续暂停。**本轮未实际执行测试，因此不得记录 Unit Test PASS。**

## 下一主线

```text
Scheduler
      ↓
Automatic Recovery
      ↓
Resume Trace Link
      ↓
Worker Trace Continuity
      ↓
Claim / Lease / Fencing
      ↓
WorkflowRuntime
      ↓
DAG / Join / Next Frontier
      ↓
Phase 2.6 Closure
```
