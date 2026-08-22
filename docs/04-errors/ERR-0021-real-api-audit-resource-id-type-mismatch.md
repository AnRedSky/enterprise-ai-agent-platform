# ERR-0021 — Real API audit query PostgreSQL resource_id type mismatch

## 1. 现象

Phase 2.1-E Real API Gate 在 Organization / Membership governance 场景中出现多处 `GET /runtime/audit-logs` 返回 HTTP 500。

一次 Gate 结果：

```text
10 failed, 20 passed
```

其中 Organization mutation 测试还出现固定组织名称冲突：

```text
409 Organization 名称已存在
```

## 2. 根因

`audit_logs.resource_id` 数据库字段为 `VARCHAR`，Organization / Membership 模型主键为 PostgreSQL `UUID`。

`RuntimeQueryService.audit_logs()` 的非 admin Organization/Membership scope 查询直接将 `AuditLog.resource_id` 与 UUID 子查询比较，PostgreSQL 会产生 `varchar = uuid` 类型不匹配并使 `/runtime/audit-logs` 返回 500。

## 3. 修复

- 在 Organization / Membership audit scope 子查询中将 UUID 主键显式 `cast(..., String)`，保持与 `AuditLog.resource_id` 的持久化类型一致。
- Real API transferred-owner 场景中的组织更新名称改为每次运行唯一，避免跨次手工 Gate 执行留下的固定名称造成 409 干扰。

## 4. 验证要求

必须重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

在开发者本地 Gate 未重新通过前，Phase 2.1-E 不得标记 Passed。
