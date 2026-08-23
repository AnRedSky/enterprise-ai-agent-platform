"""Agent Registry 兼容入口。

新代码应从 ``app.services.agent`` 导入 AgentRegistry。
"""

from app.services.agent.registry import AgentRegistry

__all__ = ["AgentRegistry"]
