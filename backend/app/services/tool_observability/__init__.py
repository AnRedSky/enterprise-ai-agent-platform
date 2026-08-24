"""Tool Observability 适配器公开入口。

职责：记录 Tool span 的开始、完成和失败事件，并写入统一 ExecutionEvent 模型。
边界：不负责 Tool 执行、权限或审计策略。
"""

from .service import ToolObservabilityAdapter

__all__ = ["ToolObservabilityAdapter"]
