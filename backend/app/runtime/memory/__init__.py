"""Memory Runtime 子模块入口。

模块职责：暴露 Memory 运行时上下文构造能力。
边界：仅负责执行期上下文格式化，不提供领域持久化服务。
关键外部依赖：context.build_memory_context。
"""

from .context import build_memory_context

__all__ = ["build_memory_context"]
