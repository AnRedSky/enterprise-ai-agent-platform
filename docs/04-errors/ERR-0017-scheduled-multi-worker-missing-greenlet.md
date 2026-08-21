# ERR-0017 — Scheduled Trigger Multi-worker MissingGreenlet / Execution ID

- Legacy ID: `2026-08-21-scheduled-multi-worker-missing-greenlet`
- Phase: Phase 1.7 scheduling
- 日期: 2026-08-21

## 现象
真实 scheduler recovery / multi-worker 场景出现 `MissingGreenlet`，同时 `workflow_executions.id` 出现 NULL NOT NULL violation。

## 根因
SQLAlchemy ORM Python-side UUID default 不会替 Core INSERT values 自动生成 id；scheduler 多 worker 的 pre-check + insert 也没有在事务边界序列化；rollback 后继续访问 expired AsyncSession ORM 实例触发隐式 IO。

## 修复
显式生成 `execution_id=uuid.uuid4()` 同时用于 ORM/Core INSERT；同一 scheduled slot 使用 PostgreSQL transaction advisory lock + atomic `INSERT ... ON CONFLICT DO NOTHING`；scheduler 每个 Trigger 使用独立 AsyncSession。

## 验证
必须真实 PostgreSQL 执行 Backend regression、migration/head 和 Real API；同一 slot 最终只能有一条 Execution，winner id 非空，loser 不得出现未处理 MissingGreenlet。
