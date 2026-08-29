"""验证 Phase 2.10-I Alembic 分支在告警生命周期迁移前正确汇合。

该测试只验证迁移拓扑，不复制生产业务规则；核心约束是 0045 必须等待两个 0044 分支完成，
其中运行时运维分支负责创建 runtime_alert_rules。
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_migration(filename: str):
    """加载指定 Alembic migration 模块以检查 revision 元数据。"""
    path = Path(__file__).parents[2] / "alembic" / "versions" / filename
    spec = spec_from_file_location(filename[:-3], path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_alert_lifecycle_migration_joins_both_0044_branches():
    """0045 必须在运行时运维与 Webhook Provider 两个 0044 分支完成后执行。"""
    migration = _load_migration("0045_alert_lifecycle_notifications.py")

    assert set(migration.down_revision) == {
        "0044_runtime_operations_enterprise",
        "0044_webhook_destination_provider",
    }


def test_alert_rule_escalation_remains_downstream_of_alert_lifecycle():
    """0046 必须继续位于 0045 之后，避免提前修改 runtime_alert_rules。"""
    migration = _load_migration("0046_alert_rule_escalation.py")

    assert migration.down_revision == "0045_alert_lifecycle_notifications"
