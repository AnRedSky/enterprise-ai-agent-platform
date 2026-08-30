"""Runtime 指标导出规范。

职责：集中维护 Prometheus / OTLP 的规范指标名、标签与资源属性，避免不同导出器自行定义第二套命名规则。
边界：只负责导出格式与值校验，不读取数据库、不计算业务指标，也不改变 Runtime Durable facts。
"""

from __future__ import annotations

import math
import time
from typing import Mapping
from uuid import UUID


class RuntimeMetricContract:
    """提供 Runtime 指标导出的规范名称、标签和安全序列化规则。"""

    PROMETHEUS_NAMES = {
        "runtime.delivery.success_percent": "runtime_delivery_success_percent",
        "runtime.delivery.retry_count": "runtime_delivery_retry_count",
        "runtime.delivery.dead_letter_count": "runtime_delivery_dead_letter_count",
        "runtime.delivery.p95_latency_ms": "runtime_delivery_p95_latency_ms",
    }
    OTLP_NAMES = tuple(PROMETHEUS_NAMES.keys())
    PROMETHEUS_LABELS = ("tenant_id",)
    OTEL_RESOURCE_ATTRIBUTES = ("service.name", "service.version", "tenant.id")
    SERVICE_NAME = "enterprise-ai-agent-platform.runtime"
    SERVICE_VERSION = "0.1.0"

    @classmethod
    def otel_resource(cls, tenant_id: UUID) -> dict[str, str]:
        """构造唯一规范的 OpenTelemetry Resource 属性集合。

        Args:
            tenant_id: 当前租户标识，作为 Resource 的 tenant.id 属性写入。

        Returns:
            包含 service.name、service.version 和 tenant.id 的 Resource 属性。
        """
        return {
            "service.name": cls.SERVICE_NAME,
            "service.version": cls.SERVICE_VERSION,
            "tenant.id": str(tenant_id),
        }

    @staticmethod
    def _number(value: float | int | None) -> float:
        """校验并规范化导出数值。

        Args:
            value: 待导出的数值；空值统一按零处理。

        Returns:
            可安全写入 Prometheus / OTLP 的有限浮点数。

        Raises:
            ValueError: 数值不是有限数字时抛出。
        """
        number = 0.0 if value is None else float(value)
        if not math.isfinite(number):
            raise ValueError("Runtime metric value must be finite")
        return number

    @staticmethod
    def _escape_label(value: str) -> str:
        """转义 Prometheus 标签值中的反斜杠、引号和换行符。"""
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    @classmethod
    def _validate_values(cls, values: Mapping[str, float | int | None]) -> None:
        """校验输入指标全部属于 canonical contract。

        Args:
            values: 待导出的 canonical 指标和值。

        Returns:
            无返回值；输入合法时正常返回。

        Raises:
            KeyError: 输入包含未定义指标时抛出。
        """
        unknown = set(values) - set(cls.PROMETHEUS_NAMES)
        if unknown:
            raise KeyError(f"unsupported runtime metrics: {sorted(unknown)}")

    @classmethod
    def _canonical_items(cls, values: Mapping[str, float | int | None]):
        """按 canonical 定义顺序返回本次实际提供的指标，允许合法子集导出。"""
        cls._validate_values(values)
        return ((name, values[name]) for name in cls.PROMETHEUS_NAMES if name in values)

    @classmethod
    def prometheus(cls, tenant_id: UUID, values: Mapping[str, float | int | None]) -> str:
        """生成租户隔离的规范 Prometheus 文本。

        Args:
            tenant_id: 当前租户标识，只允许作为唯一业务标签输出。
            values: 内部 canonical 指标名与数值，可为完整集合或合法子集。

        Returns:
            Prometheus text exposition 内容。

        Raises:
            KeyError: 出现未定义的 Runtime 指标名时抛出。
        """
        label = cls._escape_label(str(tenant_id))
        return "\n".join(
            f"{cls.PROMETHEUS_NAMES[name]}{{tenant_id=\"{label}\"}} {cls._number(value)}"
            for name, value in cls._canonical_items(values)
        ) + "\n"

    @classmethod
    def otlp(cls, tenant_id: UUID, values: Mapping[str, float | int | None]) -> dict:
        """生成 tenant-safe 的 OTLP HTTP JSON 指标结构。

        Args:
            tenant_id: 当前租户标识，写入 Resource 属性而不是业务 metric label。
            values: 内部 canonical 指标名与数值，可为完整集合或合法子集。

        Returns:
            符合 OTLP HTTP JSON 结构的指标对象。

        Raises:
            KeyError: 出现未定义的 Runtime 指标名时抛出。
        """
        timestamp = str(time.time_ns())
        metrics = [
            {
                "name": name,
                "gauge": {
                    "dataPoints": [
                        {"asDouble": cls._number(value), "timeUnixNano": timestamp}
                    ]
                },
            }
            for name, value in cls._canonical_items(values)
        ]
        resource = cls.otel_resource(tenant_id)
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": key, "value": {"stringValue": value}}
                            for key, value in resource.items()
                        ]
                    },
                    "scopeMetrics": [
                        {"scope": {"name": cls.SERVICE_NAME}, "metrics": metrics}
                    ],
                }
            ]
        }


__all__ = ["RuntimeMetricContract"]
