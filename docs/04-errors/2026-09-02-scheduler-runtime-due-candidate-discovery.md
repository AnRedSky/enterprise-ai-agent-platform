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
- 最小 Definition Contract 中 `nodes` 必须为非空数组

这里在 Discovery 层执行 **最小结构可调度性检查**：要求 `nodes` 存在且至少包含一个数组元素，因此同时排除 `definition={}`、`nodes=[]` 等无法通过 Workflow Definition 最小契约的历史脏版本。完整 DAG 语义仍由 `WorkflowRuntime.validate_definition()` 保持唯一校验入口，避免 Repository 复制 Runtime 算法。

## 第三层根因：Acceptance 错误地把全局 Runtime Counter 当成测试租户唯一事实

第二层修复后，共享 PostgreSQL 中存在其他租户的合法到期 Scheduled Schedule。当前 Runtime 的设计是多租户全库轮询，因此 `eligible`、`dispatched`、`recovered` 属于 **本次 tick 的全局运行计数**，不能被单个验收租户解释为唯一值。

## 第三层修复

Acceptance 不再把全局 Counter 当成测试数据唯一性证明，而改为：

1. 仍要求本次 Runtime 至少发现并分发一个任务，证明 tick 实际执行。
2. 对测试租户严格查询 `workflow_schedule_slots`、`workflow_executions`、`workflow_frontiers`、`audit_logs`、`workflow_trace_events`，验证本测试的执行闭环。
3. Due Candidate 边界测试先从全局候选集中筛选测试租户，再断言该租户只有 target candidate；不再假设其他租户不存在合法到期任务。
4. 所有测试数据继续使用随机 UUID 动态创建，并在 `finally` 中按测试租户清理，不要求手工修改 ID 或生产数据。

## 第四层根因：异步 SQLAlchemy Result 消费缺少 await

Acceptance 查询曾直接对 `AsyncSession.execute()` 返回的 coroutine 调用 `.mappings()`，触发 `RuntimeWarning`。项目要求 `-W error`，因此必须先 `await execute()` 再消费 Result。

## 第四层修复

统一使用：

```python
executions = (
    await verify_session.execute(
        text(...),
        {"tenant_id": tenant_id},
    )
).mappings().all()
```

该修复仅改变测试实现，不改变 Scheduler Runtime。

## 第五层根因：边界测试创建 Workflow 时违反互相引用的外键约束

`workflows.published_version_id` 外键指向 `workflow_versions.id`，同时 `workflow_versions.workflow_id` 又要求 Workflow 已存在。测试夹具原先在同一 flush 中先引用尚不存在的 Version，导致真实 PostgreSQL 拒绝插入。

## 第五层修复

`_add_published_workflow()` 在单事务中执行：

1. 创建 `published_version_id = NULL` 的 Workflow 并 `flush()`；
2. 创建并 `flush()` WorkflowVersion；
3. 参数化更新 Workflow 的 `published_version_id`。

## 第六层根因：Acceptance 错误地假设 Scheduler Tick 后 Execution 必须仍为 pending

Scheduler 只保证将 Schedule Slot 可靠投递为 Execution + Durable Frontier；并行 Worker 可以在 `tick_once()` 返回前推进 Execution。因此共享本地环境中出现 `running` 或 `completed` 是合法并发结果，不能通过停止 Worker 或固定进程顺序制造 `pending`。

## 第六层修复

Acceptance 将 Execution 状态契约调整为允许 `pending`、`running`、`completed`，同时保留 `failed` 为失败；Durable Frontier 同理允许其正常推进状态。该修复不放宽生产 Execution 状态机。

## 第七层根因：最小 Definition 检查只判断 nodes 类型，遗漏空数组

用户本地真实 PostgreSQL Gate 在第六层修复后继续执行边界测试，反馈：

```text
AssertionError: {'contention': 0, 'dispatched': 0, 'eligible': 8, 'failed': 7, ...}
assert counters["dispatched"] >= 1
```

日志显示 7 个候选在 `WorkflowRuntime.validate_definition()` 处以 `422: Workflow definition 必须包含非空 nodes` 失败。由此可以确定：之前 Discovery 的

```sql
json_typeof(definition['nodes']) = 'array'
```

只能排除缺失字段、对象等结构错误，却仍然允许 `nodes=[]`。共享 PostgreSQL 中的历史脏 Workflow 正好属于这个边界，因此它们仍然获得 lease 并进入 Trigger Service。

## 第七层修复

原先尝试使用 PostgreSQL `jsonb_path_exists(definition, '$.nodes[0]')` 来表达非空数组，但真实模型定义显示 `workflow_versions.definition` 是 SQLAlchemy `JSON`，数据库列也是 JSON 类型，而不是 JSONB。真实 PostgreSQL 验收因此报：

```text
UndefinedFunctionError: function jsonb_path_exists(json, character varying) does not exist
```

这暴露出第二个独立的类型边界错误：**Discovery SQL 使用了 JSONB-only 函数，却没有尊重实际 Schema 的 JSON 类型。**

当前修复改为 PostgreSQL JSON 原生函数：

```sql
CASE
  WHEN json_typeof(definition->'nodes') = 'array'
  THEN json_array_length(definition->'nodes')
  ELSE 0
END > 0
```

这样：

- 不需要把 JSON 列强制转换成 JSONB；
- 不依赖 JSONPath 类型转换；
- `definition={}`、`nodes=[]`、`nodes={}` 均被排除；
- 非数组值不会调用 `json_array_length`，避免类型异常；
- 完整 DAG 语义仍由 `WorkflowRuntime.validate_definition()` 负责。

## 第八层根因：Due Candidate 边界测试误把 misfire skip 场景当成正常 due dispatch 场景

在修复 JSON 边界后，真实 Gate 进入 Due Candidate 测试，Repository 候选断言已经正确通过，但 Runtime 返回：

```text
{'contention': 0, 'dispatched': 0, 'eligible': 1, 'failed': 0, ...}
```

随后测试错误地断言 `dispatched >= 1`。

根因不是 Runtime 丢失分发，而是测试数据本身同时设置了：

- `target_schedule.next_run_at = now - interval`
- `misfire_policy = skip`

`build_due_slots()` 会从 `next_run_at` 开始生成槽位。由于起点已经早于当前时间，通常会得到至少两个到期槽位；Runtime 因此进入 misfire 分支，而 `choose_misfire_slots(..., MisfirePolicy.SKIP)` 的正式契约就是返回空集合。结果是：

```text
eligible = 1
selected_slots = ()
dispatched = 0
failed = 0
```

这正是 `skip` 语义，不是调度失败。

## 第八层修复

Due Candidate dirty-data boundary 测试的职责是验证：

> disabled / future / missing Schedule / dirty Definition 不得进入当前真正可调度候选；target candidate 被发现后可以正常进入一次 Execution dispatch。

该测试不应同时承担 misfire policy 验收。因此 target Schedule 改为：

```python
next_run_at = now
misfire_policy = "skip"
```

这样 `build_due_slots()` 只生成当前槽位一个 slot，不进入 misfire compensation，`invoke_scheduled()` 可以创建正常的 Execution + Durable Frontier；misfire `skip / fire_once / catch_up` 继续由专门的 misfire 单元/Acceptance 测试覆盖。

## 当前修复提交

- `ab5f3a0dc42b454541361e2b525bd5fa09faef6c` — `fix(scheduler): use json-compatible definition boundary`
- `d7d0938e652d8003492bf91c2ef1fa959841d4e5` — `test(scheduler): cover empty nodes discovery boundary`
- `d084bf60030de244c17254f8dcfb1afe1aa1f5f4` — `docs(scheduler): record json definition type mismatch`
- `8ecd38f78762716d48182996b293407bd87f9723` — `test(scheduler): isolate due boundary from misfire semantics`

以上修复均直接提交到 `main`，没有修改服务生命周期策略，没有关闭 warning，也没有放宽 Runtime 失败语义。

## 当前验收命令

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
$env:RUN_DATABASE_INTEGRATION = "1"
uv run pytest -q -W error tests/integration/test_workflow_scheduler_runtime_boundaries.py -m integration --tb=long
```

边界测试通过后继续：

```powershell
uv run pytest -q -W error tests/integration/test_workflow_scheduler_runtime.py -m integration --tb=long
uv run pytest -q -W error tests/unit/services/workflow_scheduler/test_misfire.py tests/integration/test_workflow_scheduler_repository.py tests/integration/test_workflow_scheduler_lease_expiry.py -m "unit or integration" --tb=long
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.4\22_scheduler_runtime_gate.ps1
```

Gate 仍严格遵循“不创建、不启动、不重启、不停止 API / Scheduler / Worker / PostgreSQL / Redis”的服务生命周期约束。
