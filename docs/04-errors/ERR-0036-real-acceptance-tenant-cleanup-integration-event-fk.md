# ERR-0036 — Real PostgreSQL 验收清理 Tenant 时遗漏 Durable Integration Event 外键依赖

## 1. 现象

开发者执行：

```powershell
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

业务断言完成后，测试 `finally` 清理 Tenant 时失败：

```text
ForeignKeyViolationError: update or delete on table "tenants" violates foreign key constraint "integration_events_tenant_id_fkey" on table "integration_events"
DETAIL: Key (id)=... is still referenced from table "integration_events".
```

因此该失败发生在测试清理阶段，不代表 Retry Operator Action 的业务断言失败。

## 2. 根因

Retry 执行路径会产生 tenant-scoped Durable Integration Event。`integration_events.tenant_id` 对 `tenants.id` 使用 `ON DELETE RESTRICT`，这是为了避免租户被删除时静默丢失 Durable Event Fact。

原 Real PostgreSQL 验收夹具的清理顺序只删除了 Audit、Operator Action、Trace、Execution、Workflow、User，遗漏 `IntegrationEventRecord`，随后直接删除 Tenant，违反了真实数据库外键约束。

该问题属于验收夹具生命周期不完整，而不是生产数据库约束错误。

## 3. 修复

在验收测试清理阶段显式删除当前测试 Tenant 的 `IntegrationEventRecord`，并保持其余依赖删除顺序不变：

1. AuditLog；
2. OperatorActionIdempotency；
3. WorkflowTraceEvent；
4. IntegrationEventRecord；
5. WorkflowExecution；
6. WorkflowVersion；
7. Workflow；
8. User；
9. Tenant。

这样既遵守真实 FK 约束，也避免修改 Durable Integration Event 的生产级保留语义。

## 4. 边界判断

- 不修改 `integration_events.tenant_id` 的 `ON DELETE RESTRICT`；
- 不新增数据库 migration；
- 不通过级联删除隐藏 Durable Event Fact 的生命周期；
- 不修改 Retry / Operator Governance 生产算法；
- 不要求人工填写测试 ID、Token 或业务数据；
- 不自动启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。

## 5. 验证要求

代码修复完成后，由开发者在本地 PostgreSQL 环境重新执行：

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_result_lineage_acceptance.py -m real_api
```

然后执行统一 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
```

在开发者实际执行前，不将结果预填为“通过”。
