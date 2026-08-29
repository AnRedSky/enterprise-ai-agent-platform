"""验证 Phase 2.10-I Alembic 分支在告警生命周期迁移前正确汇合。

该测试验证迁移拓扑元数据，不复制生产业务规则；0045 通过 depends_on 等待
Runtime Operations 分支先创建 runtime_alert_rules，再执行告警生命周期表创建。
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


def test_alert_lifecycle_migration_depends_on_runtime_operations_branch():
    """0045 必须从 Webhook Provider 分支继续，并显式等待 Runtime Operations 分支。"""
    migration = _load_migration("0045_alert_lifecycle_notifications.py")

    assert migration.down_revision == "0044_webhook_destination_provider"
    assert migration.depends_on == "0044_runtime_operations_enterprise"


def test_alert_rule_escalation_remains_downstream_of_alert_lifecycle():
    """0046 必须继续位于 0045 之后，避免提前修改 runtime_alert_rules。"""
    migration = _load_migration("0046_alert_rule_escalation.py")

    assert migration.down_revision == "0045_alert_lifecycle_notifications"
