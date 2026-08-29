"""Runtime 维度时间序列采样单元测试。"""

from uuid import uuid4

import pytest

from app.services.runtime_operations.sampling import RuntimeDimensionSampler


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _DB:
    def __init__(self, grouped_rows, retry_rows):
        self.results = [_Result(grouped_rows), _Result(retry_rows)]
        self.samples = []

    async def execute(self, _statement):
        return self.results.pop(0)

    def add_all(self, samples):
        self.samples.extend(samples)

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_dimension_sampler_writes_provider_destination_event_type_samples() -> None:
    tenant_id = uuid4()
    destination_id = uuid4()
    db = _DB(
        [
            ("agent.tool.completed", destination_id, "delivered", 8),
            ("agent.tool.completed", destination_id, "dead_letter", 2),
        ],
        [("agent.tool.completed", destination_id, 3)],
    )

    count = await RuntimeDimensionSampler(db).sample(tenant_id, window_hours=24)

    assert count == 4
    assert len(db.samples) == 4
    assert {item.metric_name for item in db.samples} == {
        "runtime.delivery.total",
        "runtime.delivery.success_percent",
        "runtime.delivery.retry_count",
        "runtime.delivery.dead_letter_count",
    }
    for item in db.samples:
        assert item.tenant_id == tenant_id
        assert item.dimensions == {
            "provider": "webhook_http",
            "destination_id": str(destination_id),
            "event_type": "agent.tool.completed",
        }

    values = {item.metric_name: item.value for item in db.samples}
    assert values["runtime.delivery.total"] == 10
    assert values["runtime.delivery.success_percent"] == 80
    assert values["runtime.delivery.retry_count"] == 3
    assert values["runtime.delivery.dead_letter_count"] == 2


@pytest.mark.asyncio
async def test_dimension_sampler_is_tenant_scoped_and_empty_when_no_delivery_facts() -> None:
    db = _DB([], [])
    count = await RuntimeDimensionSampler(db).sample(uuid4())

    assert count == 0
    assert db.samples == []
