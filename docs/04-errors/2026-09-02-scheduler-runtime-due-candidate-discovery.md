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

首次 Due Candidate 修复后，共享 PostgreSQL 中仍可能存在历史已发布 Workflow，其 `published_version_id` 指向 `definition={}` 等不满足最小 Workflow Definition Contract 的版本。

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

## 第三层根因：Acceptance 错误地把全局 Runtime Counter 当成测试租户唯一事实

第二层修复后，用户本地真实 PostgreSQL 反馈为：

```text
AssertionError: {'contention': 0, 'dispatched': 2, 'eligible': 41, 'failed': 0, ...}
assert counters["eligible"] == 1
```

这一次不是生产 Runtime 又发现了 40 个错误候选，而是数据库中确实存在其他租户的合法到期 Scheduled Schedule。当前 Runtime 的设计是多租户全库轮询，因此 `eligible`、`dispatched`、`recovered` 属于 **本次 tick 的全局运行计数**，不能被单个验收租户解释为唯一值。

## 第三层修复

Acceptance 不再把全局 Counter 当成测试数据唯一性证明，而改为：

1. 仍要求本次 Runtime 至少发现并分发一个任务，证明 tick 实际执行。
2. 对测试租户严格查询 `workflow_schedule_slots`、`workflow_executions`、`workflow_frontiers`、`audit_logs`、`workflow_trace_events`，验证本测试的两个 catch-up 槽位形成唯一执行闭环。
3. Due Candidate 边界测试先从全局候选集中筛选测试租户，再断言该租户只有 target candidate；不再假设其他租户不存在合法到期任务。
4. 所有测试数据继续使用随机 UUID 动态创建，并在 `finally` 中按测试租户清理，不要求手工修改 ID 或生产数据。

这保持了 Scheduler Runtime 的多租户生产语义，同时使 PostgreSQL Acceptance 在共享开发数据库中可重复执行。

## 第四层根因：异步 SQLAlchemy Result 消费缺少 await

第三层修复后，用户本地真实 PostgreSQL Gate 继续执行到 Acceptance 查询阶段，但在读取测试租户的 `workflow_executions` 时失败：

```text
AttributeError: 'coroutine' object has no attribute 'mappings'
RuntimeWarning: coroutine 'AsyncSession.execute' was never awaited
```

根因是 `AsyncSession.execute()` 是异步方法，原测试在该查询链上直接调用：

```python
await verify_session.execute(...).mappings().all()
```

运算顺序导致 `.mappings()` 实际作用于尚未 await 的 coroutine，而不是 SQLAlchemy `Result`。这同时产生 `RuntimeWarning`，在项目“警告视为错误”的测试策略下属于必须修复的问题。

这是测试实现错误，不是 Scheduler Runtime 生产代码错误；不能通过放宽 warning 或修改生产 Runtime 来规避。

## 第四层修复

将该查询统一改为先等待 `AsyncSession.execute()`，再消费 Result：

```python
executions = (
    await verify_session.execute(
        text(...),
        {"tenant_id": tenant_id},
    )
).mappings().all()
```

并保持同一测试中其他异步查询采用相同结构。这样可以确保：

- SQL 查询真正完成后才访问 Result；
- 不再产生未 await coroutine 警告；
- `-W error` 下测试行为稳定；
- 不改变 Scheduler Runtime 生产行为或多租户计数语义。

## 第五层根因：边界测试创建 Workflow 时违反互相引用的外键约束

用户本地 Gate 在修复异步 Result 消费后继续执行，新的真实 PostgreSQL 失败为：

```text
sqlalchemy.exc.IntegrityError: ForeignKeyViolationError
Key (published_version_id)=(...) is not present in table "workflow_versions".
```

根因位于 `test_workflow_scheduler_runtime_boundaries.py` 的 `_add_published_workflow()` 测试夹具。`workflows.published_version_id` 外键指向 `workflow_versions.id`，同时 `workflow_versions.workflow_id` 又要求对应 Workflow 已存在。原夹具在同一个 flush 中直接提交带 `published_version_id=version_id` 的 Workflow 和尚不存在的 WorkflowVersion，PostgreSQL 按当前约束立即拒绝。

这属于测试数据构造顺序错误，不是生产 Scheduler Runtime 或数据库 Schema 错误。测试不得通过关闭外键、绕过约束或手工填写持久化数据规避问题。

## 第五层修复

将 `_add_published_workflow()` 调整为明确的三步事务内构造：

1. 先创建 `published_version_id = NULL` 的 Workflow 并 `flush()`，满足 `workflow_versions.workflow_id` 的父记录约束。
2. 再创建并 `flush()` 对应的 WorkflowVersion。
3. 最后使用参数化 SQL 回填 `workflows.published_version_id`，建立合法的发布版本引用。

该顺序保持事务原子性，同时真实执行数据库外键约束，避免测试夹具依赖 ORM flush 偶然顺序。

## 第六层根因：Acceptance 错误地假设 Scheduler Tick 后 Execution 必须仍为 pending

用户本地真实 PostgreSQL Gate 在修复第五层夹具后进入 Scheduler Runtime Acceptance，失败位置为：

```text
assert all(row["status"] == "pending" for row in executions)
E assert False
```

该断言隐含了“Scheduler tick 完成后没有 Worker 可以立即消费 Durable Frontier”的环境前提，但 Scheduler Runtime 的正式职责只是将 Schedule Slot 可靠地投递为 `pending Execution + Durable Frontier`；Worker 可以与 Scheduler 并行运行，并在 Scheduler `tick_once()` 返回前已经 claim Frontier、推进 Execution。

因此在共享本地 PostgreSQL 环境中，如果 Worker 正在运行，观察到 `running` 或 `completed` 是合法的并发结果，不代表 Scheduler 丢失了 Execution，也不能通过停止 Worker、固定测试进程顺序或手工准备数据库来制造 `pending` 状态。

这属于 Acceptance 测试契约错误，而不是 Scheduler Runtime 生产代码错误。

## 第六层修复

将 Scheduler Runtime Acceptance 的 Execution 状态断言调整为并发安全的契约：

- 必须存在恰好两个由测试租户产生的 Execution；
- 两个 Execution 必须与两个 Schedule Slot 一一对应；
- Execution 必须处于 `pending`、`running` 或 `completed` 之一；
- `failed` 不属于 Scheduler 成功交付的可接受结果，因此仍然立即失败；
- Durable Frontier 同理允许 `pending`、`retry_wait`、`claimed`、`running`、`completed`，以容纳 Worker 在验收查询前已经推进的合法状态。

这样既保留了对 Scheduler 持久化交付事实的严格验证，也不会把合法的 Scheduler/Worker 并发推进误判为测试失败。

## 当前修复提交

- `2d2a5a51cdd09c9bd49eca22406d81a01bdcbd21` — `test(scheduler): make runtime acceptance worker-safe`

该修复只调整 Acceptance 测试契约，没有放宽生产 Execution 状态机，也没有修改 Scheduler Runtime 的 lease、slot、idempotency 或 dispatch 逻辑。

## 边界测试

`backend/tests/integration/test_workflow_scheduler_runtime_boundaries.py` 动态生成并清理：

- 一个真正到期的 enabled + published + valid workflow；
- 一个 disabled + due + invalid definition；
- 一个 enabled + future schedule + invalid definition；
- 一个 enabled + published + invalid definition 但没有 Schedule。

测试同时直接验证 Repository 候选集与 Runtime 实际执行结果，确保：

- disabled 不进入本测试租户候选；
- future schedule 不进入本测试租户候选；
- missing schedule 不进入本测试租户候选；
- invalid published definition 不进入本测试租户候选；
- 当前目标任务不受全库脏数据影响；
- 其他租户合法到期任务不会被错误解释为本测试失败。

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
