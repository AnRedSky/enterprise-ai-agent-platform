# 2026-09-01 Operator Audit Real Acceptance actor 外键夹具错误

## 1. 问题现象

`24_operator_audit_governance_gate.ps1` 的 `Operator audit Real PostgreSQL Acceptance` 在真实 PostgreSQL 环境执行时失败：

```text
ForeignKeyViolationError: insert or update on table "audit_logs" violates foreign key constraint "audit_logs_actor_id_fkey"
DETAIL: Key (actor_id)=... is not present in table "users".
```

失败位置为 `backend/tests/api_real/test_runtime_operator_audit_acceptance.py::test_operator_audit_query_is_canonical_tenant_scoped_and_filterable`。

## 2. 根因

验收夹具在同一次 `AsyncSession` 中使用 `add_all()` 同时加入 Tenant、User、Workflow、WorkflowVersion、WorkflowExecution 和 AuditLog，然后直接 `commit()`。

`AuditLog.actor_id` 是 `users.id` 的数据库外键。该测试没有显式建立“基础身份与运行事实已经持久化”这一事务边界，因而真实 PostgreSQL 验收依赖 SQLAlchemy ORM 的 flush 排序细节。实际执行中 AuditLog 批量 INSERT 可能在 users 可见之前执行，触发数据库外键约束。

该问题不是 OperatorAuditQueryService 的查询逻辑错误，而是 Real Acceptance fixture 未显式表达其数据库依赖顺序。

## 3. 修复

将验收夹具拆为两个明确阶段：

1. 首先写入 Tenant、User、Workflow、WorkflowVersion、WorkflowExecution；
2. 执行 `await db.flush()`，确保所有 AuditLog 外键依赖在当前事务中已经进入数据库可见状态；
3. 再加入 AuditLog 并提交事务。

生产代码不增加任何绕过外键约束的逻辑，也不修改 AuditLog 数据模型。

## 4. 预防规则

- Real PostgreSQL 验收夹具涉及外键链时，必须显式构造依赖顺序，不把关键数据库约束交给隐式 ORM flush 排序。
- 测试夹具应表达真实领域持久化边界，而不是仅追求一次 `add_all()` 的简写。
- 任何 Real Acceptance 失败必须先区分生产代码缺陷与测试夹具缺陷，再决定是否修改业务实现。

## 5. 验证边界

代码修复已直接提交到 `main`。

开发者需要在本地已有 PostgreSQL 且不由 Gate 自动启动服务的前提下重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\24_operator_audit_governance_gate.ps1
```

本记录不预填本地 Gate 通过结果；只有开发者实际执行结果才能作为验收证据。
