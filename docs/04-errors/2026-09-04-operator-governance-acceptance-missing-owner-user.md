# Operator Governance PostgreSQL 验收：Workflow owner 外键缺失根因

- 日期：2026-09-04
- 范围：Phase 2.10-II / Operator Governance / PostgreSQL Acceptance
- 类型：测试夹具前置事实缺失

## 现象

Operator Action Idempotency PostgreSQL Acceptance 的两个 Retry 验收用例失败，数据库返回：

`workflows_owner_id_fkey` / `Key (owner_id) is not present in table users`

其余三个幂等验收用例通过，Backend Regression 仍保持通过。

## 根因

Retry 验收新增的 `_create_failed_execution()` 直接创建 Workflow，并将 `owner_id` 与 `WorkflowVersion.created_by` 设置为测试生成的 `user_id`，但没有先创建对应的 Tenant/User 前置事实。

PostgreSQL 正确执行 `users` 外键约束，因此失败发生在测试夹具初始化阶段，而不是 OperatorActionGovernanceService、WorkflowExecutionService 或生产事务逻辑。

## 修复

在两个 Retry 验收用例创建 Workflow 前显式调用 `_create_identity(tenant_id, user_id)`，先建立本用例独立生成的 Tenant/User，再创建 Workflow、WorkflowVersion 和 failed WorkflowExecution。

测试数据仍全部由测试自动生成，并在 `finally` 中清理；不要求开发者手工填写身份信息，也不改变生产代码。

## 防回归规则

涉及真实 PostgreSQL 的领域验收夹具必须先建立所有数据库外键所需的最小前置事实，再创建被测领域对象。测试不能绕过数据库约束，也不能通过修改生产模型来适配不完整的 fixture。

## 验证要求

必须重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\database\01_operator_governance_idempotency_acceptance.ps1
$env:PYTHONTRACEMALLOC="25"
uv run pytest -q -W error tests/integration/test_operator_action_idempotency.py -s
Remove-Item Env:PYTHONTRACEMALLOC -ErrorAction SilentlyContinue
uv run pytest -q -W error -s
uv run alembic upgrade head
```

本地未反馈新的 Acceptance 结果前，不得将该验收标记为通过。
