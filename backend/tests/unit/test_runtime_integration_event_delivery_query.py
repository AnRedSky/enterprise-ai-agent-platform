from uuid import uuid4

from app.services.runtime_query import RuntimeQueryService


class _Result:
    def __init__(self, value=None, rows=None):
        self.value = value
        self.rows = rows or []

    def scalar_one(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.rows


class _DB:
    def __init__(self, results):
        self.results = iter(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return next(self.results)


async def _query(db, tenant_id, event_id):
    return await RuntimeQueryService(db).integration_event_deliveries(tenant_id, event_id, page=1, page_size=20, status="failed")


def test_integration_event_delivery_query_is_tenant_and_event_scoped():
    import asyncio
    tenant_id = uuid4()
    event_id = uuid4()
    delivery = object()
    db = _DB([_Result(1), _Result(rows=[delivery])])

    page, page_size, total, rows = asyncio.run(_query(db, tenant_id, event_id))

    assert (page, page_size, total, rows) == (1, 20, 1, [delivery])
    params = db.statements[0].compile().params
    assert tenant_id in params.values()
    assert event_id in params.values()
