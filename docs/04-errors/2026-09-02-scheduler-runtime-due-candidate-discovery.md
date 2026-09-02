# Scheduler Runtime Due Candidate Discovery 根因记录

- 日期：2026-09-02
- 阶段：Phase 2.10-II / Scheduler Runtime
- 问题：`Scheduler Runtime PostgreSQL acceptance` 中单个测试触发器被统计为多个 eligible，并因全库历史脏 Workflow Definition 进入 `WorkflowRuntime.validate_definition()` 失败。

## 第一层根因

旧 Runtime Discovery 直接扫描全部 `scheduled + published` Trigger，并允许 `enabled/disabled` 两种状态进入候选。随后 Runtime 对每个 Trigger 调用 `ensure_schedule()`；缺失 Schedule 会使用当前时间初始化 `next_run_at`，导致历史数据在一次 tick 中被人为转化为当前到期任务。

因此 Runtime 的 `eligible` 实际表示“全库 Scheduled Trigger”，而不是“当前真正到期的 Scheduler Schedule”。disabled、future schedule、missing schedule 以及无关历史脏 Definition 都可能进入执行路径。

## 第一层修复

1. 将 Due Candidate Discovery 下沉到 `WorkflowSchedulerRepository.list_due_scheduled_candidates()`。
2. 使用单条 SQL 原子查询同时 join `WorkflowTrigger`、`Workflow`、`WorkflowSchedule`。
3. 查询强制满足：
   - `WorkflowTrigger.trigger_type = scheduled`
   - `WorkflowTrigger.status = enabled`
   - `Workflow.status = published`
   - `published_version_id IS NOT NULL`
   - `WorkflowSchedule.enabled = true`
   - `WorkflowSchedule.status = enabled`
   - `WorkflowSchedule.next_run_at <= now`
4. Runtime 不再在 tick 中遍历全库 Trigger，也不再为缺失 Schedule 隐式初始化状态。
5. Runtime 的 lease claim 仍使用已有单条 `UPDATE` 原子操作，Discovery 与 Claim 分离后继续由数据库状态收敛并处理多实例 contention。

## 第二层根因：全库存在已发布但结构非法的 Workflow Definition

首次 Due Candidate 修复后，Runtime 已经只发现真正到期的 Schedule，但共享 PostgreSQL 中仍可能存在历史已发布 Workflow，其 `published_version_id` 指向 `definition={}` 等不满足最小 Workflow Definition Contract 的版本。

这类数据如果仍进入 Due Candidate，会在获得 lease 后才由 `WorkflowRuntime.validate_definition()` 拒绝，形成：

```text
Due Candidate
  -> Lease
  -> Schedule Slot
  -> WorkflowTriggerService
  -> WorkflowRuntime.validate_definition()
  -> HTTP 422
```

这会污染 Runtime 的 `failed` 计数，并且违反“无关全库脏数据不得影响当前 tick”的 Scheduler 边界。

## 第二层修复

`list_due_scheduled_candidates()` 现在同时 join `WorkflowVersion`，并要求：

- `WorkflowVersion.id = Workflow.published_version_id`
- `WorkflowVersion.status = published`
- PostgreSQL `json_typeof(WorkflowVersion.definition['nodes']) = 'array'`

这里仅在 Discovery 层执行 **最小结构可调度性检查**：确保 `nodes` 存在且为数组；完整 DAG 语义仍由 `WorkflowRuntime.validate_definition()` 保持唯一校验入口，避免 Repository 复制 Runtime 算法。

因此非法已发布 Definition 会在进入 lease 之前被隔离，不产生 Execution、Audit、Trace 或失败事件。

## 边界测试

`backend/tests/integration/test_workflow_scheduler_runtime_boundaries.py` 动态生成并清理：

- 一个真正到期的 enabled + published + valid workflow；
- 一个 disabled + due + invalid definition；
- 一个 enabled + future schedule + invalid definition；
- 一个 enabled + published + invalid definition 但没有 Schedule。

测试同时直接验证 Repository 候选集与 Runtime 实际执行结果，确保：

- disabled 不进入候选；
- future schedule 不进入候选；
- missing schedule 不进入候选；
- invalid published definition 不进入候选；
- 当前目标任务不受全库脏数据影响。

## 验收命令

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
$env:RUN_DATABASE_INTEGRATION = "1"
uv run pytest -q -W error tests/integration/test_workflow_scheduler_runtime.py -m integration --tb=long
uv run pytest -q -W error tests/integration/test_workflow_scheduler_runtime_boundaries.py -m integration --tb=long
uv run pytest -q -W error tests/unit/services/workflow_scheduler/test_misfire.py tests/integration/test_workflow_scheduler_repository.py tests/integration/test_workflow_scheduler_lease_expiry.py -m "unit or integration" --tb=long
```

完整 Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

Gate 仍严格遵循“不创建、不启动、不重启、不停止 API / Scheduler / Worker / PostgreSQL / Redis”的服务生命周期约束。