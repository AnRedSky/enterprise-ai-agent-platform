from datetime import datetime, UTC
from uuid import uuid4

from app.models.integration_event import IntegrationEventRecord
from app.services.runtime_query import RuntimeQueryService


class _Result:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one(self):
        return self.value

    def all(self):
        return self.rows


class _DB:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


def test_integration_event_summary_is_tenant_scoped_and_aggregated():
    tenant_id = uuid4()
    db = _DB([
        _Result(3),
        _Result(rows=[("delivered", 2), ("failed", 1)]),
        _Result(rows=[("workflow", 2), ("agent", 1)]),
    ])

    import asyncio
    result = asyncio.run(
        RuntimeQueryService(db).integration_event_summary(
            tenant_id,
            occurred_from=datetime(2026, 8, 1, tzinfo=UTC),
            occurred_to=datetime(2026, 8, 31, tzinfo=UTC),
        )
    )

    assert result["total"] == 3
    assert result["status_counts"] == {"delivered": 2, "failed": 1}
    assert result["source_counts"] == {"workflow": 2, "agent": 1}
    assert result["generated_at"].tzinfo is UTC
    assert tenant_id in db.statements[0].compile().params.values()


def test_integration_event_summary_uses_event_model():
    assert IntegrationEventRecord.__tablename__ == "integration_events"
