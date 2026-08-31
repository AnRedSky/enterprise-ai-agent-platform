# Phase 2.10-II / II-04 Audit / Trace Correlation Acceptance 外键顺序错误

## 1. 问题

本地执行 `11_audit_trace_correlation_real_gate.ps1` 时，Audit / Trace Correlation Real PostgreSQL Acceptance 在 fixture 提交阶段失败：

```text
ForeignKeyViolationError: insert or update on table "audit_logs" violates foreign key constraint "audit_logs_actor_id_fkey"
Key (actor_id)=... is not present in table "users".
```

Unit / API Contract 测试未受影响，失败发生在真实 PostgreSQL fixture 初始化阶段。

## 2. 根因

Acceptance fixture 使用单次 `db.add_all(...)` 同时加入 Tenant、User、Workflow、WorkflowVersion、WorkflowExecution、WorkflowTraceEvent、AuditLog 与 OperatorActionIdempotency。

`AuditLog.actor_id` 与 `OperatorActionIdempotency.actor_id` 均存在数据库外键约束，但对应 ORM 模型之间没有足以让 SQLAlchemy Unit of Work 自动推导该插入依赖的 relationship。结果是 fixture 不能依赖 `add_all` 中对象的声明顺序保证数据库 INSERT 顺序。

这不是生产 Runtime Audit / Trace Correlation Service 的生命周期或 tenant-scope 实现错误，而是 Real Acceptance 测试 fixture 对数据库真实外键约束建模不完整。

## 3. 修复

将 fixture 初始化拆成两个明确阶段：

1. 首先插入 Tenant、User、Workflow、WorkflowVersion、WorkflowExecution、WorkflowTraceEvent，并执行 `await db.flush()`；
2. 在确认用户身份已进入数据库后，再插入 AuditLog 与 OperatorActionIdempotency 并提交事务。

这样测试直接表达数据库实际依赖关系，不修改生产表结构，也不增加 ORM relationship 仅为满足测试。

## 4. 防回归

继续保持以下断言：

- Execution → Trace / Audit / Operator Action；
- Trace → Execution / Audit / Operator Action；
- Audit → Execution / Trace / Operator Action；
- Operator Action → Execution / Audit / Trace；
- tenant isolation；
- filter 与分页；
- 测试数据自动创建与清理。

本修复后的提交只修改 Acceptance fixture，不改变 Runtime Correlation Service Contract。

## 5. 验证要求

开发者本地应依次执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_runtime_audit_trace_correlation.py tests/api_contract/test_runtime_audit_trace_correlation_contract.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\10_audit_trace_correlation_unit_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\11_audit_trace_correlation_real_gate.ps1
uv run pytest -q
```

Real Gate 仍然禁止自动启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；fixture 不要求人工填写测试身份或业务 ID。
