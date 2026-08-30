"""Runtime OpenTelemetry Meter 适配的单元测试。

职责：验证 SDK Meter、Resource、canonical metric 与 tenant 维度的一致性。
边界：不连接 PostgreSQL、Redis 或真实 Provider，不验证网络导出。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource

from app.services.runtime_operations import RuntimeMetricContract, RuntimeTelemetry


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
