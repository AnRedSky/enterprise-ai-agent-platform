# 2026-09-01 Phase 2.10-II Operator Audit PostgreSQL Acceptance await 误用

## 现象

开发者本地执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Governance Unit/API regression 已通过，Alembic migration/head verification 也已通过；PostgreSQL Acceptance 在 `test_operator_action_governance_schema_is_migration_complete` 失败，并同时产生未等待协程警告。

关键错误：

```text
AttributeError: 'coroutine' object has no attribute 'scalar_one'
RuntimeWarning: coroutine 'AsyncConnection.execute' was never awaited
```

## 根因

`AsyncConnection.execute()` 是异步方法。测试在索引查询处直接对 `connection.execute(...)` 返回的 coroutine 调用 `.scalar_one()`，没有先 `await` 获取 `CursorResult`。

前面的列查询和外键查询已经正确采用 `await connection.execute(... )` 后再读取结果，因此该错误属于同一测试函数中的异步 Result 使用不一致，而不是 PostgreSQL schema、Alembic migration 或生产查询服务缺陷。

## 修复

将索引查询拆分为两个明确步骤：

1. `index_result = await connection.execute(...)` 等待数据库执行完成；
2. `index_columns = index_result.scalar_one()` 从已解析的 `CursorResult` 读取唯一索引定义。

不修改生产代码，不修改 migration revision，不通过 `stamp` 或手工操作 `alembic_version` 绕过 migration graph。

## 验证要求

本地重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\26_operator_audit_query_performance_gate.ps1
```

Gate 必须继续保持：

- 不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；
- 测试数据由测试自动生成；
- `uv run alembic upgrade head` 成功；
- `uv run alembic heads` 只返回 `0056_merge_legacy_audit_and_operator_governance_heads`；
- PostgreSQL Acceptance 在 `-W error` 下无 warning/error；
- 服务启动边界检查无新增受保护服务进程。

## 工程结论

该问题属于测试代码的异步 API 使用错误。修复后再以开发者本地实际 Gate 结果判断 Operator Governance PostgreSQL Acceptance 是否通过；远端代码读取不能替代本地数据库验收。
