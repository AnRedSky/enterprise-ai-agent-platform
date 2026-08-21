# 2026-08-21 Scheduled Trigger Multi-worker MissingGreenlet / Execution ID

## 实际错误

Real API multi-worker scheduler contract 与 Backend 启动时的 scheduled recovery 均暴露了同一条调度持久化链路缺陷：

```text
sqlalchemy.exc.MissingGreenlet:
greenlet_spawn has not been called; can't call await_only() here.
```

以及：

```text
asyncpg.exceptions.NotNullViolationError:
null value in column "id" of relation "workflow_executions" violates not-null constraint
```

## 根因

1. `WorkflowExecution.id` 使用 SQLAlchemy Python-side `default=uuid.uuid4`，但 scheduled idempotency claim 使用 PostgreSQL `INSERT` Core statement，并显式读取新建 ORM 对象的 `execution.id`。Core `INSERT.values()` 不会替 Python ORM flush 触发该默认值，因此 `id` 实际为 `None`，导致 `workflow_executions.id` NOT NULL 约束失败。
2. 两个 scheduler worker 对同一 slot 的 pre-check + insert 原先没有在数据库事务边界上序列化。虽然 `(tenant_id, idempotency_key)` unique constraint 能阻止最终重复持久化，但并发 loser 在异常/rollback 路径上可能继续访问已经过期的 AsyncSession ORM 实例，触发隐式 reload 和 `MissingGreenlet`。
3. scheduler 原先在同一个 `AsyncSession` 中批量处理所有 candidate。一次 rollback 会使该 session 中其他 ORM candidate 进入 expired 状态，后续同步属性访问可能再次触发 `MissingGreenlet`。

## 修复方案

### 1. 显式生成 WorkflowExecution UUID

scheduled claim 在构造 `WorkflowExecution` 前直接生成 `execution_id = uuid.uuid4()`，并同时用于 ORM 对象和 Core INSERT：

```text
execution_id = uuid.uuid4()
        ↓
WorkflowExecution(id=execution_id, ...)
        ↓
INSERT ... VALUES (id=execution_id, ...)
```

因此 scheduled recovery、普通 tick 和 multi-worker claim 都不会依赖 Core INSERT 路径触发 ORM Python default。

### 2. PostgreSQL transaction advisory lock

同一个 scheduled slot 的 claim 现在先执行：

```text
pg_advisory_xact_lock(hashtext(idempotency_key))
        ↓
find existing execution
        ↓
atomic INSERT ... ON CONFLICT DO NOTHING
        ↓
commit
```

事务级 advisory lock 在 commit / rollback 时自动释放，使同一 slot 的 check + claim 在数据库边界确定性收敛。`uq_workflow_execution_tenant_idempotency` 仍保留为最终持久化正确性边界。

### 3. Scheduler candidate 按 Trigger 隔离 Session

scheduler 先只发现稳定的 Trigger primary key，然后每个 Trigger 使用独立 `AsyncSession` 查询和执行。单个 Trigger rollback 不再污染后续 candidate 的 ORM 状态，也不需要依赖 expired ORM attribute 的隐式数据库 IO。

## 影响

- Backend 启动后的 scheduled recovery 不再因 `workflow_executions.id = NULL` 失败；
- multi-worker scheduler 对同一 slot 必须最终只产生一条 `workflow_executions`；
- loser worker 不再因为 rollback 后的 ORM expired attribute 访问产生 `MissingGreenlet`；
- 真实 HTTP scheduler contract 可以严格验证 `dispatched == 1`。

## 预防措施

1. 使用 SQLAlchemy Core `insert()` 时，不能假设 ORM `mapped_column(default=...)` 会先替 Core values 生成 Python 默认值；需要显式生成主键或使用数据库 server default。
2. Async SQLAlchemy 代码禁止依赖 ORM 属性隐式 lazy reload；rollback 后尤其不能继续访问可能 expired 的实例属性。
3. 并发去重必须以数据库原子边界为准，pre-check 只能作为优化。
4. Scheduler multi-worker contract 必须使用真实 PostgreSQL + AsyncSession 验证。
5. Recovery、restart、duplicate tick 必须验证 Execution persistence，而不是只验证内存 counters。

## 验证要求

- Backend regression：`uv run pytest -q`；
- Migration/head verification：`uv run alembic upgrade head`；
- Real API Gate：`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1`；
- 两个 scheduler worker 对同一 slot 必须最终只存在一条 `workflow_executions`；
- winner Execution 的 `idempotency_key` 必须等于 `scheduled:{trigger_id}:{slot}`；
- winner Execution 必须具有非空 UUID `id`；
- loser worker 不得产生未处理的 `MissingGreenlet`。

## 状态

已直接修复并提交 `main`，等待本地真实 PostgreSQL 环境执行 Backend regression 与 Real API Gate 验证。
