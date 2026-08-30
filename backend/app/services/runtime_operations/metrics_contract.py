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
        return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")

    @classmethod
    def prometheus(cls, tenant_id: UUID, values: Mapping[str, float | int | None]) -> str:
        """生成租户隔离的规范 Prometheus 文本。

        Args:
            tenant_id: 当前租户标识，只允许作为唯一业务标签输出。
            values: 内部 canonical 指标名与数值。

        Returns:
            Prometheus text exposition 内容。

        Raises:
            KeyError: 出现未定义的 Runtime 指标名时抛出。
        """
        unknown = set(values) - set(cls.PROMETHEUS_NAMES)
        if unknown:
            raise KeyError(f"unsupported runtime metrics: {sorted(unknown)}")
        label = cls._escape_label(str(tenant_id))
        return "\n".join(
            f"{cls.PROMETHEUS_NAMES[name]}{{tenant_id=\"{label}\"}} {cls._number(values[name])}"
            for name in cls.PROMETHEUS_NAMES
        ) + "\n"

    @classmethod
    def otlp(cls, tenant_id: UUID, values: Mapping[str, float | int | None]) -> dict:
        """生成 tenant-safe 的 OTLP HTTP JSON 指标结构。

        Args:
            tenant_id: 当前租户标识，写入 Resource 属性而不是业务 metric label。
            values: 内部 canonical 指标名与数值。

        Returns:
            符合 OTLP HTTP JSON 结构的指标对象。

        Raises:
            KeyError: 出现未定义的 Runtime 指标名时抛出。
        """
        unknown = set(values) - set(cls.OTLP_NAMES)
        if unknown:
            raise KeyError(f"unsupported runtime metrics: {sorted(unknown)}")
        timestamp = str(time.time_ns())
        metrics = [
            {
                "name": name,
                "gauge": {
                    "dataPoints": [
                        {"asDouble": cls._number(values[name]), "timeUnixNano": timestamp}
                    ]
                },
            }
            for name in cls.OTLP_NAMES
        ]
        return {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": cls.SERVICE_NAME}},
                            {"key": "service.version", "value": {"stringValue": cls.SERVICE_VERSION}},
                            {"key": "tenant.id", "value": {"stringValue": str(tenant_id)}},
                        ]
                    },
                    "scopeMetrics": [
                        {"scope": {"name": cls.SERVICE_NAME}, "metrics": metrics}
                    ],
                }
            ]
        }


__all__ = ["RuntimeMetricContract"]
