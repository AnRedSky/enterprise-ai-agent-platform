"""Phase 2.10-I Runtime Enterprise Operations 的真实 PostgreSQL 验收。

职责：验证 Provider Registry、Alert Rule、Metric Snapshot/Series、Prometheus/OTLP Export、Runtime Telemetry 与 Operational Audit 的真实持久化和租户边界。
边界：不启动任何服务，不执行外部 Provider 网络请求；测试数据由用例自动创建和清理。
"""

from __future__ import annotations

import uuid

import pytest
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from sqlalchemy import delete

from app.infrastructure.db.session import SessionLocal
from app.models.core import Tenant
from app.models.runtime_operations import (
    RuntimeAlertRule,
    RuntimeMetricSample,
    RuntimeOperationAudit,
    RuntimeProviderRegistry,
)
from app.services.runtime_operations import RuntimeMetricContract, RuntimeOperationsEnterpriseService, RuntimeOperationsService, RuntimeTelemetry

pytestmark = pytest.mark.real_api


@pytest.mark.asyncio
async def test_runtime_enterprise_registry_metrics_export_audit_are_tenant_scoped() -> None:
    """验证企业 Runtime 运维能力从注册到指标出口均保持 tenant scope。"""
    suffix = uuid.uuid4().hex[:12]
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    actor = f"acceptance-{suffix}"
    try:
        async with SessionLocal() as db:
            db.add_all([
                Tenant(id=tenant_a, name=f"phase-210-i-a-{suffix}", status="active"),
                Tenant(id=tenant_b, name=f"phase-210-i-b-{suffix}", status="active"),
            ])
            await db.flush()
            service = RuntimeOperationsEnterpriseService(db)
            provider = await service.create_provider(
                tenant_a,
                f"primary-{suffix}",
                "webhook_http",
                {"capabilities": ["delivery", "healthcheck"], "timeout_seconds": 5},
                actor,
            )
            rule = await service.create_alert_rule(
                tenant_a,
                f"delivery-slo-{suffix}",
                "runtime.delivery.success_percent",
                "<",
                99.0,
                5,
                "critical",
                actor,
            )
            await db.commit()
            provider_id, rule_id = provider.id, rule.id

        async with SessionLocal() as db:
            service = RuntimeOperationsEnterpriseService(db)
            assert [item.id for item in await service.providers(tenant_a)] == [provider_id]
            assert await service.providers(tenant_b) == []
            assert [item.id for item in await service.alerts_rules(tenant_a)] == [rule_id]
            assert await service.alerts_rules(tenant_b) == []

            sample_count = await service.snapshot(tenant_a, window_hours=24)
            assert sample_count >= 4
            await db.commit()

            series = await service.series(tenant_a, "runtime.delivery.success_percent", window_minutes=60)
            assert series
            assert all(item.tenant_id == tenant_a for item in series)
            assert await service.series(tenant_b, "runtime.delivery.success_percent", window_minutes=60) == []

            prometheus = await service.prometheus(tenant_a)
            assert "runtime_delivery_success_percent" in prometheus
            assert f'tenant_id="{tenant_a}"' in prometheus
            assert str(tenant_b) not in prometheus

            otlp = await service.otlp(tenant_a)
            resource = otlp["resourceMetrics"][0]["resource"]
            attributes = {item["key"]: item["value"]["stringValue"] for item in resource["attributes"]}
            assert attributes == RuntimeMetricContract.otel_resource(tenant_a)
            assert all("tenant_id" not in item for item in otlp["resourceMetrics"][0]["scopeMetrics"][0]["metrics"])

            overview = await RuntimeOperationsService(db).overview(tenant_a, window_hours=24)
            canonical_values = {
                "runtime.delivery.success_percent": overview["slo"]["delivery_success_percent"],
                "runtime.delivery.retry_count": overview["deliveries"]["retry_count"],
                "runtime.delivery.dead_letter_count": overview["deliveries"]["dead_letter_count"],
            }
            telemetry_reader = InMemoryMetricReader()
            telemetry_provider = MeterProvider(
                resource=Resource.create(RuntimeMetricContract.otel_sdk_resource()),
                metric_readers=[telemetry_reader],
            )
            telemetry = RuntimeTelemetry(telemetry_provider)
            telemetry.record(tenant_a, canonical_values)
            telemetry_data = telemetry_reader.get_metrics_data()
            assert telemetry_data is not None
            telemetry_resource = telemetry_data.resource_metrics[0].resource.attributes
            assert telemetry_resource == RuntimeMetricContract.otel_sdk_resource()
            telemetry_names = {metric.name for metric in telemetry_data.resource_metrics[0].scope_metrics[0].metrics}
            assert telemetry_names == set(canonical_values)
            assert telemetry_names.issubset(RuntimeMetricContract.OTLP_NAMES)
            for metric in telemetry_data.resource_metrics[0].scope_metrics[0].metrics:
                point = next(iter(metric.data.data_points))
                assert point.attributes == {RuntimeMetricContract.OTEL_METRIC_ATTRIBUTES[0]: str(tenant_a)}
            telemetry.shutdown()

            audits = await service.audit_list(tenant_a)
            assert {"provider.create", "alert_rule.create"}.issubset({item.action for item in audits})
            assert await service.audit_list(tenant_b) == []
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(RuntimeOperationAudit).where(RuntimeOperationAudit.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeMetricSample).where(RuntimeMetricSample.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeAlertRule).where(RuntimeAlertRule.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(RuntimeProviderRegistry).where(RuntimeProviderRegistry.tenant_id.in_([tenant_a, tenant_b])))
            await db.execute(delete(Tenant).where(Tenant.id.in_([tenant_a, tenant_b])))
            await db.commit()


@pytest.mark.asyncio
async def test_runtime_metric_contract_keeps_tenant_boundary_for_both_export_formats() -> None:
    """验证 Prometheus 与 OTLP 导出都不会混入其他租户标识或未知指标。"""
    tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
    prometheus = RuntimeMetricContract.prometheus(
        tenant_a, {"runtime.delivery.success_percent": 100.0}
    )
    otlp = RuntimeMetricContract.otlp(
        tenant_b, {"runtime.delivery.success_percent": 100.0}
    )
    assert str(tenant_b) not in prometheus
    assert otlp["resourceMetrics"][0]["resource"]["attributes"][-1]["value"]["stringValue"] == str(tenant_b)
    with pytest.raises(KeyError):
        RuntimeMetricContract.prometheus(tenant_a, {"runtime.unknown": 1})
