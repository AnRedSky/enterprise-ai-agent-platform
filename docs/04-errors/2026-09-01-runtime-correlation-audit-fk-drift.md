# 2026-09-01：Runtime Correlation Acceptance 因历史 Audit 外键约束失败

## 1. 现象

最新 `main` 的 Runtime Audit / Trace Correlation Real PostgreSQL Acceptance 在写入历史兼容 `AuditLog.execution_id` 时失败：

```text
ForeignKeyViolationError: insert or update on table "audit_logs" violates foreign key constraint "fk_audit_execution"
Key (execution_id)=... is not present in table "executions".
```

失败入口：

```text
backend/tests/api_real/test_runtime_audit_trace_correlation_acceptance.py
```

## 2. 根因

当前 `AuditLog.execution_id` 已被明确设计为历史兼容字段，只用于读取早期可观测性数据，不再属于当前 Workflow Execution 领域的正式关系。当前正式关联字段是 `workflow_execution_id`。

生产 ORM 已移除 `execution_id -> executions.id` 的 `ForeignKey`，但已有 PostgreSQL 数据库仍可能保留旧数据库约束 `fk_audit_execution`。因此 ORM 元数据与实际数据库约束发生漂移：代码允许历史审计记录使用已经不存在于 `executions` 表的旧 ID，数据库却继续拒绝写入。

这不是 Runtime Correlation 查询逻辑错误，而是数据库迁移缺失导致的 schema drift。

## 3. 修复

新增 Alembic migration：

```text
backend/alembic/versions/0013_remove_legacy_audit_execution_fk.py
```

升级时使用：

```sql
ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS fk_audit_execution
```

因此：

- 已存在旧约束的数据库可以被修复；
- 新数据库没有该约束时升级安全跳过；
- `workflow_execution_id` 的正式外键关系保持不变；
- `execution_id` 继续作为历史兼容普通 UUID 字段；
- 不删除历史数据，也不要求手工修改测试 fixture。

## 4. Gate 修复

Runtime Correlation Backend Gate 在 PostgreSQL readiness 通过后执行：

```powershell
uv run alembic upgrade head
```

然后再执行 Real PostgreSQL Acceptance。

该步骤只执行数据库迁移，不启动、重启或停止任何 API、Worker、Scheduler、PostgreSQL 或 Redis 服务，符合项目服务自动启动边界。

## 5. 验证要求

本地执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\23_runtime_correlation_contract_hardening_gate.ps1
```

Gate 必须覆盖：

1. Unit regression；
2. API Contract；
3. PostgreSQL readiness；
4. Alembic upgrade head；
5. Real PostgreSQL Acceptance；
6. targeted regression；
7. Backend default regression，并将 warning 视为 error；
8. 服务启动边界检查。

## 6. 后续约束

任何删除或替换数据库外键关系的领域重构，必须同步提供 Alembic migration，并在 Backend Gate 中实际执行 `uv run alembic upgrade head` 验证，避免 ORM metadata 与 PostgreSQL schema 再次漂移。
