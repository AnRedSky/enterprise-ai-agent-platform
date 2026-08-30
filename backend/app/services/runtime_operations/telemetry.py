"""Runtime OpenTelemetry 观测适配。

职责：将 RuntimeMetricContract 的规范指标值桥接到 OpenTelemetry SDK Meter，并固定 service / tenant Resource 边界。
边界：不读取数据库、不替代 RuntimeMetricContract，也不负责 Prometheus / OTLP 网络导出；指标事实仍由 Runtime Operations Service 维护。
关键依赖：opentelemetry-api、opentelemetry-sdk。
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.metrics import Observation

from .metrics_contract import RuntimeMetricContract


class RuntimeTelemetry:
    """提供与 RuntimeMetricContract 对齐的 OpenTelemetry Meter。"""

    def __init__(self, provider: MeterProvider | None = None) -> None:
        """创建 Runtime Meter，并固定服务资源属性。

        Args:
            provider: 可选的 SDK MeterProvider；未提供时创建独立 Provider，便于应用入口和测试显式管理生命周期。
        """
        self.provider = provider or MeterProvider(
            resource=Resource.create(
                {
                    "service.name": RuntimeMetricContract.SERVICE_NAME,
                    "service.version": RuntimeMetricContract.SERVICE_VERSION,
                }
            )
        )
        self.meter = self.provider.get_meter(RuntimeMetricContract.SERVICE_NAME)
        self._values: dict[tuple[str, str], float] = {}
        self._instruments = {
            name: self.meter.create_observable_gauge(
                name,
                description=f"Runtime metric {name}",
                unit="1",
                callbacks=[self._callback(name)],
            )
            for name in RuntimeMetricContract.OTLP_NAMES
        }

    def _callback(self, metric_name: str):
        """创建单指标观察回调，保持 tenant 作为唯一业务维度。"""
        def observe(_options):
            return [
                Observation(value, {"tenant_id": tenant_id})
                for (name, tenant_id), value in self._values.items()
                if name == metric_name
            ]

        return observe

    def record(self, tenant_id: UUID, values: Mapping[str, float | int | None]) -> None:
        """记录一次 Runtime 指标快照供 SDK Meter 观察。

        Args:
            tenant_id: 当前租户标识。
            values: RuntimeMetricContract 定义的 canonical 指标值。

        Returns:
            无返回值。

        Raises:
            KeyError: values 包含未知 Runtime 指标时抛出。
            ValueError: 指标值不是有限数字时抛出。
        """
        unknown = set(values) - set(RuntimeMetricContract.OTLP_NAMES)
        if unknown:
            raise KeyError(f"unsupported runtime metrics: {sorted(unknown)}")
        tenant = str(tenant_id)
        for name, value in values.items():
            self._values[(name, tenant)] = RuntimeMetricContract._number(value)

    def shutdown(self) -> None:
        """关闭 SDK MeterProvider，释放其异步导出资源。"""
        self.provider.shutdown()


__all__ = ["RuntimeTelemetry"]
