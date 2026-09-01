# 2026-09-01 Operator Governance migration 多 head 与数据库事实漂移

## 1. 问题现象

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，Operator Audit targeted regression 暴露：

1. PostgreSQL 中 `audit_logs.operator_action_id` 不存在，而 ORM `AuditLog` 与 Runtime Audit / Trace Correlation 已经依赖该字段；
2. Alembic 执行 `upgrade head` 报告存在多个 head，导致真实数据库验收无法进入 migration 与 PostgreSQL acceptance 阶段。

随后第二次执行 targeted regression 已通过，但 migration gate 明确输出：

```text
0013_remove_legacy_audit_execution_fk (head)
0055_operator_audit_operator_action_index (head)
```

## 2. 根因

当前 migration graph 存在两个没有被最终 merge 收敛的分支：

- `0012_execution_event_metadata -> 0013_remove_legacy_audit_execution_fk`；
- `0053_operator_action_result_resource_type -> 0054_merge_operator_governance_heads -> 0055_operator_audit_operator_action_index`。

此前 `0054_merge_operator_governance_heads` 只合并了 `0048_operator_action_audit_lineage`、`0051_operator_audit_query_indexes`、`0053_operator_action_result_resource_type` 三个 Operator Governance 分支，并未包含历史 `0013_remove_legacy_audit_execution_fk`。

因此 `0055` 继续位于 Operator Governance 分支末端时，历史 `0013` 仍然是独立 head。`uv run alembic upgrade head` 无法选择唯一目标，导致 Gate 停止。

第一次 Contract 失败中的 `audit_logs.operator_action_id` 缺失属于数据库事实与当前 ORM/Contract 不一致的表现；当前 Contract 已通过 Service mock 隔离真实数据库，第二次执行已证明该 Contract 路径本身已经恢复稳定。migration graph 的多 head 是本次 Gate 无法进入真实 PostgreSQL 验收的独立阻塞因素。

## 3. 修复

- 保留 `0048_operator_action_audit_lineage` 的 `depends_on = "0049_operator_action_idempotency"`；
- 保留 `0054_merge_operator_governance_heads` 原有三分支 merge，不重写历史 revision；
- 保留 `0055_operator_audit_operator_action_index` 的 Canonical Operator Audit 查询索引；
- **新增 `0056_merge_legacy_audit_and_operator_governance_heads`，父节点为 `0055_operator_audit_operator_action_index` 与 `0013_remove_legacy_audit_execution_fk`，将两个现存 head 收敛为唯一 head；**
- 不修改 `alembic_version`，不使用 `stamp` 绕过 migration，不删除历史 migration，不重写已经存在的 revision ID。

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

本修复采用新增 merge migration 收敛历史分支，不修改已发布 revision 的父节点，避免破坏已经应用旧 migration 的数据库环境。`0056` 是纯 merge 节点，业务 DDL 仍由既有父 migration 提供，因此不会重复创建或删除历史 schema。
