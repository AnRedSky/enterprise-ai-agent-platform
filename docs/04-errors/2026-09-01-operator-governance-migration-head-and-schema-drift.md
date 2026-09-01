# 2026-09-01 Operator Governance migration 多 head 与数据库事实漂移

## 1. 问题现象

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Audit targeted regression 暴露：

1. PostgreSQL 中 `audit_logs.operator_action_id` 不存在，而 ORM `AuditLog` 与 Runtime Audit / Trace Correlation 已经依赖该字段；
2. Alembic 执行 `upgrade head` 报告存在多个 head，导致真实数据库验收无法进入 migration 与 PostgreSQL acceptance 阶段。

同时，当前 `OperatorActionIdempotency` ORM 已使用 `result_resource_type`，而早期 `0049_operator_action_idempotency` migration 创建表时没有该列；后续已有 `0053_operator_action_result_resource_type` 已负责补齐该字段。

## 2. 根因

当前 migration graph 实际存在三条 Operator Governance 相关分支：

- `0047 -> 0048_operator_action_audit_lineage`；
- `0049 -> 0050 -> 0051_runtime_operator... -> 0052_runtime_audit_action_outcome_index -> 0053_operator_action_result_resource_type`；
- `0050 -> 0051_operator_audit_query_indexes`。

其中 `0048_operator_action_audit_lineage` 与主链在 `0047` 分叉；Canonical Operator Audit 查询又从 `0050` 分叉；这些分支没有最终 merge revision，因此 `alembic upgrade head` 无法确定唯一目标。

本次本地错误中的 `audit_logs.operator_action_id` 缺失，是因为数据库升级无法跨过多 head，导致 `0048_operator_action_audit_lineage` 未被应用。

## 3. 修复

- 恢复原有 `0053_operator_action_result_resource_type` migration，不修改已经存在的 revision 语义；该 migration 同时负责历史成功结果类型回填及失败结果清理；
- 新增 `0054_merge_operator_governance_heads`，一次性合并：
  - `0053_operator_action_result_resource_type`；
  - `0051_operator_audit_query_indexes`；
  - `0048_operator_action_audit_lineage`；
- merge migration 不重复创建业务结构，只负责收敛 Alembic graph；
- 保留历史 `0050_runtime_audit_query_indexes` 与既有 `0052_runtime_audit_action_outcome_index`，不修改已发布 migration；
- Runtime Audit / Trace Correlation 单元测试 mock 已同步覆盖直接 Operator Action → Audit 查询路径；
- 新增 PostgreSQL Acceptance，验证 `audit_logs.operator_action_id`、`operator_action_idempotencies.result_resource_type` 及 Operator Action → AuditLog 外键实际存在。

## 4. 验证设计

Gate 必须依次执行：

1. Backend Unit / API Contract；
2. PostgreSQL readiness；
3. `uv run alembic upgrade head`；
4. `uv run alembic heads` 并确认只有一个 head；
5. Operator Action → AuditLog → Result Resource PostgreSQL Acceptance；
6. 服务启动边界检查。

Gate 不自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。

## 5. 设计边界

本修复采用 additive merge migration 收敛历史分支，不重写 `0048/0049/0050/0051/0052/0053` 已存在的 revision ID，避免破坏可能已经应用这些 migration 的数据库环境。
