# Phase 1.7-A-03 — Scheduled Trigger Governance / Failure & Recovery Contract

## 目标

在 Phase 1.7-A-02 的真实 Scheduler Runtime 之上，补齐调度失败、Workflow 状态变化与进程重启场景的治理边界，确保 Scheduler 仍然只通过现有 Workflow Execution Runtime 进入业务执行链路。

## 本阶段 Contract

### 1. Dispatch failure

- Scheduler 单个 Trigger dispatch 失败不得终止整个 scheduler loop；
- 当前 tick 统计 `failed`，记录结构化日志，并继续处理其他 Trigger；
- 如果 `invoke_scheduled()` 已创建 Execution 后 Runtime 失败，Execution 必须保持真实 `failed` 状态并保留已有 audit/trace；
- Scheduler 不创建第二条绕过 Runtime 的补偿 Execution。

### 2. Workflow / Trigger governance

Scheduler candidate 必须同时满足：

- `WorkflowTrigger.trigger_type = scheduled`；
- `WorkflowTrigger.status = enabled`；
- `Workflow.status = published`；
- `Workflow.published_version_id` 非空。

因此：

- Trigger disabled 后不再 dispatch；
- Workflow unpublish / archive 后不再 dispatch；
- 删除 Trigger 后下一次扫描自然不再命中。

### 3. Same-slot recovery

Scheduler 使用：

```text
scheduled:{trigger_id}:{interval_slot}
```

作为唯一的调度幂等边界。

同一 Trigger + slot 即使发生：

- scheduler tick 重复；
- FastAPI worker 重启后重新扫描；
- 多 worker 同时 dispatch；

也不得产生第二个 Workflow Execution。

如果该 slot 已存在 `failed` Execution，仍视为该 slot 已消费，不自动复制 Execution。失败恢复进入后续 slot 或显式 operator retry，而不是破坏 idempotency contract。

### 4. Restart boundary

重启不持久化 scheduler `next_run_at`。重启后的第一轮扫描直接根据当前 UTC 时间计算 interval slot，并通过数据库唯一约束收敛重复 dispatch。

因此 Phase 1.7-A-03 暂不引入 migration。

## 验收范围

### Unit

- retry Runtime 在下一次 attempt 前必须经历 `failed -> running`；
- workflow deadline 超过 retry backoff 时记录 `node.retry.exhausted` + `reason=workflow_deadline`；
- same-slot idempotency key 保持稳定。

### Real API / Runtime

- Scheduled Trigger 自动执行失败时 Execution 保持 `failed`；
- 失败 Execution 仍可通过既有 Execution governance 查询；
- 同 slot 再次 scheduler poll 不产生第二 Execution；
- Trigger disabled 后不产生新的 slot Execution；
- Workflow unpublish 后不产生新的 slot Execution；
- 重新 publish 后下一有效 slot 可以恢复 dispatch；
- scheduler restart 不重复消费已存在 slot。

## Migration Decision

**暂不需要 migration。**

只有在需要持久化 `next_run_at`、scheduler lease、misfire policy、失败重试状态或 Cron 表达式时，才进入新的数据库状态模型与 migration 设计。

## 下一步

Phase 1.7-A-04：Scheduled Trigger Production Hardening / Multi-worker Concurrency Contract。

重点转向数据库唯一约束竞态、scheduler worker 并发、锁粒度、poll drift 与可观测指标。
