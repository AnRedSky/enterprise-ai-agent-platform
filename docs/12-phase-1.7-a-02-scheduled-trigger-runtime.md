# Phase 1.7-A-02 — Scheduled Trigger Runtime / Scheduler Execution Contract

## 目标

在 Phase 1.7-A-01 的 Scheduled Trigger API Contract 之上，建立第一版真实 Scheduler Runtime：

- 后端进程启动时启动 Scheduler background task；
- 周期扫描 `enabled + scheduled + published Workflow`；
- 通过现有 Workflow Execution Runtime 执行，不绕过治理与审计；
- 使用确定性的 interval-slot Idempotency-Key，避免同一调度窗口产生重复 Execution；
- 多 worker 重复 dispatch 时依赖已有数据库唯一约束收敛到单个 Execution；
- Scheduler 停止时随 FastAPI lifespan 一起取消。

## 当前 Contract

Scheduled Trigger config：

```json
{
  "timezone": "Asia/Shanghai",
  "interval_seconds": 60
}
```

第一版使用 interval slot，而不是 Cron。`interval_seconds` 决定调度窗口；`timezone` 保持为 IANA timezone contract。由于当前 Trigger 是“间隔触发”而非“本地日历 Cron”，elapsed interval 不需要对 timezone 做日历换算。

Scheduler Idempotency-Key：

```text
scheduled:{trigger_id}:{interval_slot}
```

其中 `interval_slot = floor(UTC_epoch_seconds / interval_seconds)`。

## Runtime Flow

```text
FastAPI lifespan
    ↓
ScheduledTriggerScheduler.run_forever()
    ↓
tick_once()
    ↓
DB: enabled + scheduled + published Workflow
    ↓
validate scheduled config
    ↓
deterministic Idempotency-Key
    ↓
WorkflowTriggerService.invoke_scheduled()
    ↓
WorkflowExecutionService.create()
    ↓
Governance audit / trace
    ↓
WorkflowExecutionService.run()
    ↓
completed / failed Execution
```

## Migration Decision

Phase 1.7-A-02 **暂不需要 migration**。

原因：调度状态没有增加新的持久化字段。当前实现利用：

- `workflow_triggers.config` 保存 interval/timezone；
- `workflow_triggers.status` 控制 enabled/disabled；
- `workflows.status + published_version_id` 控制可执行 Published Workflow；
- `workflow_executions.idempotency_key` + tenant unique constraint 提供 interval-slot 去重。

如果后续需要持久化 `next_run_at`、失败重试状态、scheduler lease、misfire policy 或 Cron expression，再单独进入 migration 设计。

## 验收范围

### Unit

- interval slot 在同一窗口保持稳定；
- interval boundary 正确切换；
- Idempotency-Key 对同一 Trigger + slot 稳定；
- 下一 slot 生成不同 key；
- invalid scheduler settings 被拒绝。

### Real API

- Scheduled Trigger create/detail/update；
- 非法 timezone 返回 422；
- Scheduled Trigger 不允许通过普通 `/invoke` 手工调用；
- Scheduler 自动创建 Execution；
- Execution 最终 completed；
- 同一 interval slot 不产生第二个 Execution；
- Trigger disabled 后不再进入 scheduler candidate；
- Trigger 删除后 detail 返回 404。

## 下一步

Phase 1.7-A-03：Scheduled Trigger Governance / Failure & Recovery Contract。

重点验证 scheduler dispatch failure、Workflow unpublish/disable、Execution failure、restart 后同 slot 去重，以及后续是否需要持久化 scheduler state。
