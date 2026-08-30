"""验证 Runtime Prometheus / OTLP / OpenTelemetry SDK 指标导出的规范契约与租户边界。"""

from uuid import uuid4

import pytest

from app.services.runtime_operations.metrics_contract import RuntimeMetricContract


VALUES = {
    "runtime.delivery.success_percent": 99.25,
    "runtime.delivery.retry_count": 2,
    "runtime.delivery.dead_letter_count": 1,
    "runtime.delivery.p95_latency_ms": None,
}


def test_otel_resource_uses_canonical_service_and_tenant_attributes() -> None:
    """OpenTelemetry OTLP Resource 属性必须由 canonical contract 单一入口生成。"""
    tenant_id = uuid4()
    assert RuntimeMetricContract.otel_resource(tenant_id) == {
        "service.name": RuntimeMetricContract.SERVICE_NAME,
        "service.version": RuntimeMetricContract.SERVICE_VERSION,
        "tenant.id": str(tenant_id),
    }


def test_otel_sdk_resource_is_process_scoped() -> None:
    """共享 SDK MeterProvider 只能使用进程级 Resource，tenant 必须留在 Metric 维度。"""
    assert RuntimeMetricContract.otel_sdk_resource() == {
        "service.name": RuntimeMetricContract.SERVICE_NAME,
        "service.version": RuntimeMetricContract.SERVICE_VERSION,
    }
    assert RuntimeMetricContract.OTEL_METRIC_ATTRIBUTES == ("tenant_id",)


def test_prometheus_uses_canonical_names_and_only_tenant_label() -> None:
    """Prometheus 只能暴露规范指标名和 tenant_id 标签，避免任意业务维度泄漏到出口。"""
    tenant_id = uuid4()
    output = RuntimeMetricContract.prometheus(tenant_id, VALUES)

    lines = output.strip().splitlines()
    assert [line.split("{", 1)[0] for line in lines] == list(RuntimeMetricContract.PROMETHEUS_NAMES.values())
    assert all(line.count("{") == 1 and line.count("}") == 1 for line in lines)
    assert all(f'tenant_id="{tenant_id}"' in line for line in lines)
    assert all(line.count(",") == 0 for line in lines)
    assert lines[-1].endswith(" 0.0")


def test_prometheus_escapes_tenant_label_and_rejects_unknown_metric() -> None:
    """Prometheus 标签必须安全转义，未知指标不得静默进入公共出口。"""
    tenant_id = uuid4()
    escaped = RuntimeMetricContract._escape_label("a\\\"\n")
    assert escaped.startswith("a")
    assert "\\\\" in escaped
    assert '\\"' in escaped
    assert "\\n" in escaped

    with pytest.raises(KeyError):
        RuntimeMetricContract.prometheus(tenant_id, {"runtime.unknown": 1})


def test_prometheus_rejects_non_finite_values() -> None:
    """NaN 与无穷值不能进入监控出口。"""
    with pytest.raises(ValueError, match="finite"):
        RuntimeMetricContract.prometheus(uuid4(), {"runtime.delivery.success_percent": float("nan")})


def test_prometheus_accepts_a_canonical_metric_subset() -> None:
    """Prometheus 可以导出合法 canonical 子集，不得因其他指标未采样而 KeyError。"""
    tenant_id = uuid4()
    output = RuntimeMetricContract.prometheus(
        tenant_id, {"runtime.delivery.success_percent": 100.0}
    )
    assert output.strip() == (
        f'runtime_delivery_success_percent{{tenant_id="{tenant_id}"}} 100.0'
    )


def test_otlp_uses_resource_tenant_attribute_and_canonical_names() -> None:
    """OTLP 将 tenant 放在 Resource 属性中，并保持内部 canonical 指标名不变。"""
    tenant_id = uuid4()
    payload = RuntimeMetricContract.otlp(tenant_id, VALUES)
    resource = payload["resourceMetrics"][0]["resource"]
    attributes = {item["key"]: item["value"]["stringValue"] for item in resource["attributes"]}
    metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]

    assert attributes == RuntimeMetricContract.otel_resource(tenant_id)
    assert [item["name"] for item in metrics] == list(RuntimeMetricContract.OTLP_NAMES)
    assert all("tenant_id" not in item for item in metrics)
    assert all("timeUnixNano" in item["gauge"]["dataPoints"][0] for item in metrics)


def test_otlp_accepts_a_canonical_metric_subset() -> None:
    """OTLP 可以导出合法 canonical 子集，并保持 tenant 只存在于 Resource。"""
    tenant_id = uuid4()
    payload = RuntimeMetricContract.otlp(
        tenant_id, {"runtime.delivery.success_percent": 100.0}
    )
    metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
    assert [item["name"] for item in metrics] == ["runtime.delivery.success_percent"]
    assert metrics[0]["gauge"]["dataPoints"][0]["asDouble"] == 100.0
