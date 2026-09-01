# 2026-09-01 Operator Governance migration 多 head 与数据库事实漂移

## 1. 问题现象

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Audit targeted regression 暴露两类问题：

1. PostgreSQL 中 `audit_logs.operator_action_id` 不存在，而 ORM `AuditLog` 与 Runtime Audit / Trace Correlation 已经依赖该字段；
2. Alembic 执行 `upgrade head` 报告存在多个 head，导致真实数据库验收无法进入 migration 与 PostgreSQL acceptance 阶段。

同时，当前 `OperatorActionIdempotency` ORM 已使用 `result_resource_type`，而早期 `0049_operator_action_idempotency` migration 创建表时没有该列，形成第二处 migration 与模型事实漂移。

## 2. 根因

`0048_operator_action_audit_lineage` 是在 `0047_merge_runtime_operations_alerts` 之后独立加入的 migration，而主链上的 `0048_webhook_delivery_consumer_group` 同样以 `0047` 为父 revision，形成两个 Alembic head。随后 `0049_operator_action_idempotency -> 0050 -> 0051` 只沿主链继续，未将 Operator Action → AuditLog 关联分支合并回 Canonical migration graph。

因此新代码已经声明：

- `AuditLog.operator_action_id`；
- `OperatorActionIdempotency.result_resource_type`；
- Operator Action → AuditLog → Result Resource 关联查询；

但数据库升级路径不能稳定把这些结构全部落地。

## 3. 修复

新增 `0052_merge_operator_audit_lineage`：

- 同时继承 `0051_operator_audit_query_indexes` 与 `0048_operator_action_audit_lineage`；
- 只负责合并 migration graph，不重复创建业务结构；
- 使 Alembic 恢复单一 head；
- 由于 `0049` 已先创建 `operator_action_idempotencies`，合并分支中的 `0048_operator_action_audit_lineage` 可以在数据库升级时安全创建 `audit_logs.operator_action_id` 外键。

新增 `0053_operator_action_result_resource_type`：

- 为 `operator_action_idempotencies` 增加 `result_resource_type`；
- 不重复创建 ORM 已定义的 `ix_operator_action_result_resource` 索引；
- 使结果资源 ID 与资源类型形成显式 Contract。

同步修正 Runtime Audit / Trace Correlation 单元测试 mock，使测试事实与新增的直接 Operator Action → Audit 查询路径一致，不通过修改生产代码回避真实查询。

## 4. 验证设计

新增 PostgreSQL Acceptance：

- 检查 `audit_logs.operator_action_id` 实际存在；
- 检查 `operator_action_idempotencies.result_resource_type` 实际存在；
- 检查 `audit_logs.operator_action_id -> operator_action_idempotencies.id` 外键实际存在。

Gate 必须先执行 `uv run alembic upgrade head`，再执行 Real PostgreSQL Acceptance；不允许把 migration 未完成伪装成查询测试通过。

## 5. 设计边界

本修复不删除 `0050_runtime_audit_query_indexes`，因为它属于历史 `runtime_operation_audits` 查询能力，删除已执行 migration 会破坏既有数据库环境。

本修复也不修改已经发布的 `0048/0049/0050/0051` revision ID，只通过新的 merge revision 收敛 migration graph，并通过后续 additive migration 补齐缺失字段。
