# 2026-08-26 Scheduler Deadlock 与 Real API Execution Response 问题记录

## 1. 现象

Tenant Safe Real API Gate 出现两类失败：

1. Runtime Model Governance 测试在 Worker 抢占竞态下拿到 `{"detail": ...}` HTTP 错误体，测试随后访问 `persisted["status"]` 触发 `KeyError`。
2. Scheduler recovery 场景出现 PostgreSQL `DeadlockDetectedError`，导致历史 recovery slot 没有正确推进，`counters["recovered"]` 为 0。

## 2. 根因

### Execution Helper

`run_or_observe_execution()` 原先在 `expected_http_status` 命中 4xx/5xx 时直接返回 HTTP 错误 JSON。该返回值并不是 WorkflowExecution Contract，因此调用方无法可靠读取 `status`、`error_code` 等持久化字段。

### Scheduler

`ScheduledTriggerScheduler.tick_once()` 在同一个数据库事务中持有 Schedule lease 行，同时执行 Slot/Execution 写入并最终推进 Schedule。独立 Worker 与多个 Scheduler consumer 参与后，数据库锁获取顺序可能形成：

```text
Scheduler transaction: schedule -> execution/slot
Worker transaction:    execution -> schedule
```

从而形成 PostgreSQL lock inversion / deadlock。

## 3. 修复

### Execution Helper

保留真实 `/run` HTTP 状态码，同时对预期的 4xx/5xx 重新查询 `/workflows/executions/{id}`，直到 Execution 进入终态，再返回统一的持久化 Execution 结构。

### Scheduler

将 Scheduler 调度过程拆成明确的持久化事务边界：

```text
1. claim Schedule lease -> commit
2. claim Slot / create-or-reuse Execution / bind Slot -> commit
3. advance Schedule + release lease -> commit
```

这样 Worker 不再与 Scheduler 共享一个跨阶段事务锁集合，降低并发运行时的反向锁等待风险，同时保留 Slot 唯一键和 Schedule owner fencing 作为幂等与 ownership 边界。

## 4. 验证要求

本修复必须通过：

- Worker / fencing unit tests
- Checkpoint unit / integration tests
- 完整 `uv run pytest -q`
- Backend regression gate
- Tenant Safe Real API Gate
- Scheduler / Worker persisted recovery acceptance

所有 Real API / Recovery Gate 均不得自动启动、停止或重启本地 API、Scheduler、Worker 服务。
