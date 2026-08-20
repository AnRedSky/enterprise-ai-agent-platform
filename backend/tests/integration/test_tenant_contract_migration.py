from __future__ import annotations

import importlib.util
from pathlib import Path


class _MigrationOpSpy:
    def __init__(self) -> None:
        self.executed: list[object] = []

    def execute(self, statement: object) -> None:
        self.executed.append(statement)

    def __getattr__(self, _name: str):
        def noop(*_args, **_kwargs) -> None:
            return None

        return noop


def _load_migration():
    migration_path = Path(__file__).parents[1] / "alembic" / "versions" / "0015_tenant_contract.py"
    spec = importlib.util.spec_from_file_location("tenant_contract_migration", migration_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tenant_contract_migration_casts_bound_uuid_values_for_postgresql():
    migration = _load_migration()
    spy = _MigrationOpSpy()
    migration.op = spy

    migration.upgrade()

    sql = [str(statement) for statement in spy.executed]
    assert any("CAST(:id AS UUID)" in statement for statement in sql)
    assert any("CAST(:tenant_id AS UUID)" in statement for statement in sql)
