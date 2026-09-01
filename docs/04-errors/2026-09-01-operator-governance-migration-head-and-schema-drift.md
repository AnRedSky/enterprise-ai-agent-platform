# 2026-09-01 Operator Governance migration 多 head 与数据库事实漂移

## 1. 问题现象

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Audit targeted regression 暴露：

1. PostgreSQL 中 `audit_logs.operator_action_id` 不存在，而 ORM `AuditLog` 与 Runtime Audit / Trace Correlation 已经依赖该字段；
2. Alembic 执行 `upgrade head` 报告存在多个 head，导致真实数据库验收无法进入 migration 与 PostgreSQL acceptance 阶段。

当前 `OperatorActionIdempotency` ORM 使用 `result_resource_type`，而早期 `0049_operator_action_idempotency` 创建表时没有该列；后续已有 `0053_operator_action_result_resource_type` 负责补齐该字段。

## 2. 根因

当前 migration graph 存在多个 Operator Governance 相关分支：

- `0047 -> 0048_operator_action_audit_lineage`；
- `0049 -> 0050 -> 0051_runtime_operator... -> 0052_runtime_audit_action_outcome_index -> 0053_operator_action_result_resource_type`；
- `0050 -> 0051_operator_audit_query_indexes`。

`0048_operator_action_audit_lineage` 虽然从 `0047` 独立产生，但其 DDL 外键依赖 `0049_operator_action_idempotency` 创建的 `operator_action_idempotencies` 表。原 migration 未声明这一运行时依赖。

因此这里同时存在两个工程问题：migration graph 多 head，以及独立 lineage 分支缺少 DDL 依赖声明。多 head 又使 `upgrade head` 无法继续，最终表现为数据库缺失 `audit_logs.operator_action_id`。

## 3. 修复

- 保留原有 `0048/0049/0050/0051/0052/0053` revision ID；
- 为 `0048_operator_action_audit_lineage` 增加 `depends_on = "0049_operator_action_idempotency"`，保证全新数据库先创建 Operator Action 表，再创建 AuditLog 外键；
- 新增 `0054_merge_operator_governance_heads`，一次性合并：
  - `0053_operator_action_result_resource_type`；
  - `0051_operator_audit_query_indexes`；
  - `0048_operator_action_audit_lineage`；
- 恢复原有 `0053_operator_action_result_resource_type`，保留结果类型回填与失败结果清理逻辑；
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

本修复采用 `depends_on + additive merge migration` 收敛历史分支，不重写已经存在的 revision ID，也不删除历史 Runtime Audit migration，避免破坏已经应用这些 migration 的数据库环境。
