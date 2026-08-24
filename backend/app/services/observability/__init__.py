"""Observability 领域服务公开入口。

职责：统一记录 Execution 生命周期与 ExecutionEvent 运行事件，并提供 trace/request 标识生成能力。
边界：不负责业务执行、模型调用或审计策略；只维护运行可观测性的持久化记录。
"""

from .service import ObservabilityService

__all__ = ["ObservabilityService"]
