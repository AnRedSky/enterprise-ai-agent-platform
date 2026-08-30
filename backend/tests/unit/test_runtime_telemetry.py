"""Runtime OpenTelemetry Meter 适配的单元测试。

职责：验证 SDK Meter、Resource、canonical metric、tenant 维度，以及 Scheduler 到 SDK Meter 的事实桥接。
边界：不连接 PostgreSQL、Redis 或真实 Provider，不验证网络导出。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource

from app.services.runtime_operations import RuntimeMetricContract, RuntimeTelemetry
from app.services.runtime_operations.scheduler import RuntimeAlertScheduler


def test_runtime_telemetry_uses_canonical_resource_and_metric_names() -> None:
    """验证 SDK Meter 使用统一服务 Resource，并暴露 canonical Runtime 指标。"""
    reader = InMemoryMetricReader()
    provider = MeterProvider(
        resource=Resource.create(
            {
                "service.name": RuntimeMetricContract.SERVICE_NAME,
                "service.version": RuntimeMetricContract.SERVICE_VERSION,
            }
        ),
        metric_readers=[reader],
    )
    telemetry = RuntimeTelemetry(provider)
    tenant_id = uuid4()
    telemetry.record(
        tenant_id,
        {
            "runtime.delivery.success_percent": 99.5,
            "runtime.delivery.retry_count": 2,
            "runtime.delivery.dead_letter_count": 1,
            "runtime.delivery.p95_latency_ms": 120,
        },
    )

    data = reader.get_metrics_data()
    assert data is not None
    scope = data.resource_metrics[0].scope_metrics[0]
    names = {metric.name for metric in scope.metrics}
    assert names == set(RuntimeMetricContract.OTLP_NAMES)
    resource = data.resource_metrics[0].resource.attributes
    assert resource["service.name"] == RuntimeMetricContract.SERVICE_NAME
    assert resource["service.version"] == RuntimeMetricContract.SERVICE_VERSION
    for metric in scope.metrics:
        point = next(iter(metric.data.data_points))
        assert point.attributes == {"tenant_id": str(tenant_id)}

    telemetry.shutdown()


def test_runtime_telemetry_rejects_unknown_metric() -> None:
    """验证 SDK 观测入口不会接受 RuntimeMetricContract 未定义的指标。"""
    telemetry = RuntimeTelemetry()
    with pytest.raises(KeyError):
        telemetry.record(uuid4(), {"runtime.unknown": 1})
    telemetry.shutdown()


def test_runtime_telemetry_rejects_non_finite_metric() -> None:
    """验证 SDK 入口继续复用 canonical 指标的有限值约束。"""
    telemetry = RuntimeTelemetry()
    with pytest.raises(ValueError):
        telemetry.record(uuid4(), {"runtime.delivery.retry_count": float("nan")})
    telemetry.shutdown()


@pytest.mark.asyncio
async def test_runtime_alert_scheduler_bridges_durable_slo_to_telemetry() -> None:
    """验证 Scheduler 从 Runtime Operations Durable facts 生成 SDK Meter 快照。"""
    tenant_id = uuid4()
    db = MagicMock()
    telemetry = MagicMock()
    scheduler = RuntimeAlertScheduler(60)
    scheduler.set_telemetry(telemetry)
    overview = {
        "slo": {
            "delivery_success_percent": 98.5,
            "p95_delivery_latency_ms": 240.0,
        },
        "deliveries": {
            "retry_count": 3,
            "dead_letter_count": 2,
        },
    }

    with patch(
        "app.services.runtime_operations.scheduler.RuntimeOperationsService"
    ) as service_factory:
        service_factory.return_value.overview = AsyncMock(return_value=overview)
        await scheduler._sync_telemetry(tenant_id, db)

    service_factory.assert_called_once_with(db)
    telemetry.record.assert_called_once_with(
        tenant_id,
        {
            "runtime.delivery.success_percent": 98.5,
            "runtime.delivery.retry_count": 3,
            "runtime.delivery.dead_letter_count": 2,
            "runtime.delivery.p95_latency_ms": 240.0,
        },
    )
