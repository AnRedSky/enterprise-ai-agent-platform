# Phase 2.10-II / II-05 批量 Operator Action Real Acceptance 租户清理外键错误

## 1. 错误现象

`tests/api_real/test_batch_operator_actions_acceptance.py::test_batch_operator_action_is_tenant_scoped_and_partially_completable` 在真实 PostgreSQL Acceptance 的 `finally` 清理阶段失败。

错误为：

```text
ForeignKeyViolationError:
update or delete on table "tenants" violates foreign key constraint
"integration_events_tenant_id_fkey" on table "integration_events"
```

此前 Unit、API Contract 与 Backend Regression 均通过，失败只发生在 Real PostgreSQL 的测试数据清理阶段。

## 2. 根因

批量 `workflow_execution.cancel` 复用了既有 Workflow Execution Domain Service。取消成功后会产生 Durable Integration Event。测试原有清理顺序只删除 `AuditLog`、`WorkflowExecution`、`WorkflowVersion`、`Workflow`、`User` 和 `Tenant`，遗漏了 `integration_events`。

`IntegrationEventRecord.tenant_id` 对 `tenants.id` 使用 `ON DELETE RESTRICT`，因此租户仍被 Durable Integration Event 引用时不能删除。

该问题属于 Acceptance Fixture 清理不完整，不是生产业务状态机或 tenant boundary 实现错误。

## 3. 修复

在删除测试租户之前显式删除当前用例创建租户下的 `IntegrationEventRecord`。

`WebhookDelivery.integration_event_id` 对 Integration Event 使用 `ON DELETE CASCADE`，因此依赖事件的 Delivery 会随事件一并清理，不需要复制第二套 Delivery 清理逻辑。

## 4. 防回归

Real Acceptance 继续验证：

- 同批次跨租户资源不会越权；
- 当前租户资源成功取消；
- 外部租户资源被拒绝；
- 合法资源的状态变更保持 `cancelled`；
- 清理阶段能够删除本用例生成的完整 Durable Event 事实。

## 5. 验证要求

本修复提交后必须由开发者本地执行：

```powershell
cd backend
uv run pytest -q -m real_api tests/api_real/test_batch_operator_actions_acceptance.py --tb=short
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\12_controlled_batch_operations_unit_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\13_controlled_batch_operations_real_gate.ps1
uv run pytest -q
```

测试 Gate 不创建、启动、重启或停止任何服务。
