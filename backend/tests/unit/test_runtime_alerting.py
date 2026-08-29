from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.runtime_operations.alerting import OPERATORS, RuntimeAlertEvaluator


@pytest.mark.parametrize(
    ("operator", "value", "threshold", "expected"),
    [
        (">", 10, 5, True),
        (">=", 5, 5, True),
        ("<", 4, 5, True),
        ("<=", 5, 5, True),
        ("==", 5, 5, True),
    ],
)
def test_supported_alert_operators(operator, value, threshold, expected):
    assert OPERATORS[operator](value, threshold) is expected


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _DB:
    def __init__(self, rules, samples):
        self.rules = rules
        self.samples = iter(samples)
        self.added = []

    async def execute(self, _statement):
        return _Result(self.rules)

    async def scalar(self, _statement):
        return next(self.samples, None)

    def add(self, item):
        self.added.append(item)


@pytest.mark.asyncio
async def test_evaluator_is_tenant_scoped_and_returns_firing_state():
    tenant_id = uuid4()
    rule = SimpleNamespace(
        id=uuid4(), name="delivery-slo", metric_name="runtime.delivery.success_percent",
        operator="<", threshold=99.0, window_minutes=15, severity="critical", enabled=True,
    )
    sample = SimpleNamespace(
        id=uuid4(), tenant_id=tenant_id, metric_name=rule.metric_name, value=97.5,
        recorded_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db = _DB([rule], [sample])

    result = await RuntimeAlertEvaluator(db).evaluate(tenant_id)

    assert len(result) == 1
    assert result[0]["state"] == "firing"
    assert result[0]["metric_name"] == rule.metric_name
    assert db.added == []


@pytest.mark.asyncio
async def test_evaluator_ignores_rules_without_recent_samples():
    tenant_id = uuid4()
    rule = SimpleNamespace(
        id=uuid4(), name="retry", metric_name="runtime.delivery.retry_count",
        operator=">", threshold=0, window_minutes=15, severity="warning", enabled=True,
    )
    db = _DB([rule], [None])

    result = await RuntimeAlertEvaluator(db).evaluate(tenant_id)

    assert result == []
