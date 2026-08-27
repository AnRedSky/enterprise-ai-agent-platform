# Phase 2.6 — Scheduler Trace Context

## 状态

开发中（Scheduler → Recovery Trace 收口阶段）。

## 本轮完成

新增 `WorkflowSchedulerTraceService` 与 `SchedulerTraceContext`，为 Scheduler scan 建立统一 Recovery Telemetry 生命周期边界：

```text
Scheduler scan
    ↓
start_scan()
    ↓
trace_id
    ↓
RECOVERY_SCAN_COMPLETED
    ↓
finish_trace()
```

Scheduler 不直接依赖具体 OpenTelemetry / Prometheus SDK，而是复用 `WorkflowRecoveryTelemetry`。

## Trace 约束

- 一个 Scheduler scan 只生成一个稳定 `trace_id`。
- scan completed 与 trace finished 必须使用同一 `trace_id`。
- Scheduler trace 不携带 checkpoint `state_data`、prompt、secret 或 provider credential。
- Scheduler trace 只记录调度统计、execution identity、phase、outcome 与耗时等控制面信息。
- 本层只定义生命周期契约；实际 `ScheduledTriggerScheduler.tick_once()` 接入下一步完成，避免在 Contract 层复制调度执行逻辑。

## Unit Test

新增 `backend/tests/unit/test_workflow_scheduler_trace.py`，覆盖成功 scan 与失败 scan 的 trace 生命周期、统计字段和 outcome。

按照开发准则，只有实际执行 pytest 后才能记录 PASS；当前未执行完整测试流程。

## 下一任务

将 `ScheduledTriggerScheduler.tick_once()` 接入该 Trace Service，并把 `trace_id` 持久化传递到 Automatic Recovery / Resume Trace Link，最终形成：

```text
Scheduler
  ↓
Automatic Recovery
  ↓
Resume Execution
  ↓
Worker
  ↓
WorkflowRuntime
  ↓
DAG / Join
  ↓
Checkpoint
```

完整回归、E2E、Browser 与 Release Gate 继续暂停。
