# 2026-08-29 Phase 2.10-I Alembic 分支迁移顺序错误

## 现象

在数据库位于 `0043_webhook_delivery_audit` 时执行 `uv run alembic upgrade heads`，迁移先成功执行 `0044_webhook_destination_provider`，随后执行 `0045_alert_lifecycle_notifications` 失败：

```text
UndefinedTableError: relation "runtime_alert_rules" does not exist
```

失败 DDL 为创建 `runtime_alert_instances` 时建立 `runtime_alert_rules(id)` 外键。

## 根因

Phase 2.10-I 同时存在两个从 `0043_webhook_delivery_audit` 分叉的 `0044` migration：

- `0044_runtime_operations_enterprise`：创建 `runtime_alert_rules`、`runtime_provider_registry`、`runtime_metric_samples`、`runtime_operation_audits`。
- `0044_webhook_destination_provider`：补充 `webhook_destinations.provider`。

原 `0045_alert_lifecycle_notifications` 只声明 `down_revision = "0044_webhook_destination_provider"`，因此 Alembic 在执行 0045 时并未保证运行时运维分支已经完成，导致其外键目标表不存在。

## 修复

将 0045 改为同时依赖两个 0044 分支：

```python
down_revision = (
    "0044_runtime_operations_enterprise",
    "0044_webhook_destination_provider",
)
```

这样迁移拓扑收敛为：

```text
0043
 ├─ 0044_runtime_operations_enterprise ─┐
 └─ 0044_webhook_destination_provider ──┴─ 0045_alert_lifecycle_notifications → 0046_alert_rule_escalation
```

## 为什么不直接调整 revision 编号

两个 0044 已经进入远端 `main` 且可能存在本地数据库记录，修改 revision ID 会造成已有环境迁移身份不一致。保留 revision ID，仅修正 0045 的多父依赖可以让尚未完成迁移的环境正确汇合，同时不改变已经成功记录 0045 的数据库迁移身份。

## 验证要求

必须在本地 PostgreSQL 实际执行：

```powershell
cd backend
uv run alembic heads
uv run alembic upgrade heads
uv run alembic current
uv run pytest -q tests/unit/test_migration_graph.py --tb=short
```

最终应只剩 `0046_alert_rule_escalation` 一个 head，并且 `runtime_alert_rules`、`runtime_alert_instances`、`runtime_notification_policies`、`runtime_notification_groups`、`runtime_notification_deliveries` 均完成创建。
