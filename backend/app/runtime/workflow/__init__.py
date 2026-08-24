"""Workflow Runtime 领域公共入口。

职责：统一暴露 Workflow Runtime 相关的运行时能力。
边界：不承载 Workflow Service 生命周期管理；具体执行编排继续由 `workflow_runtime.py` 负责。
关键依赖：Workflow Circuit Breaker 等 Runtime 组件。
"""

from .circuit_breaker import CircuitBreakerService, CircuitOpenError

__all__ = ["CircuitBreakerService", "CircuitOpenError"]
