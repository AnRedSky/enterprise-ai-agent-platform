# 2026-08-21 Scheduled Trigger Multi-worker MissingGreenlet

## 实际错误

Real API multi-worker scheduler contract 在两个 scheduler worker 并发执行同一历史 slot 时出现：

```text
sqlalchemy.exc.MissingGreenlet:
greenlet_spawn has not been called; can't call await_only() here.
```

同时日志显示两个 worker 对同一 `(tenant_id, idempotency_key)` 竞争写入 `workflow_executions`，其中一个事务触发了 PostgreSQL unique constraint：

```text
uq_workflow_execution_tenant_idempotency
```

## 根因

并发 IntegrityError 处理路径在当前 SQLAlchemy AsyncSession 状态下继续访问已经过期的 ORM `workflow` 实例属性，触发隐式数据库 reload。该 reload 发生在不具备 SQLAlchemy greenlet context 的同步属性访问中，因此产生 `MissingGreenlet`。

原问题并非数据库唯一约束设计错误；唯一约束本身正是 slot execution 的最终持久化去重边界。

## 影响

- multi-worker scheduler Real API contract 失败；
- 失败 worker 在异常处理过程中不能稳定返回 convergence 结果；
- 不影响普通单 worker scheduled execution 的核心 persistence contract。

## 修复方案

main 已采用数据库事务边界上的 slot claim serialization：

```text
pg_advisory_xact_lock(hashtext(idempotency_key))
        ↓
find existing execution
        ↓
create / dispatch
```

事务级 advisory lock 在事务提交或 rollback 时自动释放，使同一 slot 的 check + dispatch 在数据库边界收敛。

同时保留 `(tenant_id, idempotency_key)` unique constraint 作为最终持久化正确性边界。

## 预防措施

1. Async SQLAlchemy 代码禁止依赖 ORM 属性隐式 lazy reload。
2. 并发去重必须以数据库原子边界为准，pre-check 只能作为优化。
3. Scheduler multi-worker contract 必须使用真实 PostgreSQL + AsyncSession 验证。
4. Recovery、restart、duplicate tick 必须验证 Execution persistence，而不是只验证内存 counters。

## 验证要求

- Backend regression：实际执行并记录结果；
- Real API Gate：实际执行并记录结果；
- 两个 scheduler worker 对同一 slot 必须最终只存在一条 `workflow_executions`；
- winner Execution 的 `idempotency_key` 必须等于 `scheduled:{trigger_id}:{slot}`；
- loser worker 不得产生未处理的 `MissingGreenlet`。

## 状态

已修复并进入后续 Phase 1.7-B persistence contract 回归验证；本阶段不再增加额外并发绕路方案。
