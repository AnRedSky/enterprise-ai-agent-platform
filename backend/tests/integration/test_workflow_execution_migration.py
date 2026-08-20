from __future__ import annotations

import importlib.util
from pathlib import Path


class _MigrationOpSpy:
    def __init__(self) -> None:
        self.created_tables: list[tuple] = []
        self.created_indexes: list[tuple] = []

    def create_table(self, *args, **kwargs):
        self.created_tables.append((args, kwargs))

    def create_index(self, *args, **kwargs):
        self.created_indexes.append((args, kwargs))

    def drop_index(self, *args, **kwargs):
        return None

    def drop_table(self, *args, **kwargs):
        return None


def _load_migration():
    # tests/integration -> backend -> alembic/versions
    path = Path(__file__).parents[2] / "alembic" / "versions" / "0016_workflow_execution_state_machine.py"
    spec = importlib.util.spec_from_file_location("workflow_execution_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_execution_migration_creates_execution_and_node_tables():
    migration = _load_migration()
    spy = _MigrationOpSpy()
    migration.op = spy

    migration.upgrade()

    names = [args[0] for args, _kwargs in spy.created_tables]
    assert names == ["workflow_executions", "workflow_node_executions"]
    assert any(args[0] == "ix_workflow_execution_tenant_created" for args, _ in spy.created_indexes)
    assert any(args[0] == "ix_workflow_node_execution_execution_created" for args, _ in spy.created_indexes)
