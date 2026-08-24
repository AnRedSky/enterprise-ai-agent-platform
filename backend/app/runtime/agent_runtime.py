"""Agent Runtime：负责将 Agent 上下文组装为模型请求并执行。

职责：构造 system/history/user 消息，并通过统一 Model Gateway 执行生成或流式生成。
边界：不实现 Provider 路由、模型治理或外部 Provider 适配；这些职责分别由 Model 领域与 infrastructure/providers 承担。
关键依赖：Agent 模型、`app.runtime.model` 的统一 Gateway。
"""

from typing import AsyncIterator
from uuid import UUID

from app.models.agent import Agent
from app.runtime.model import ModelGateway, ModelResult


class AgentRuntime:
    """Agent 执行 Runtime，复用统一模型 Gateway，不复制模型调用实现。"""

    def __init__(self):
        self.gateway = ModelGateway()

    @staticmethod
    def build_messages(agent: Agent, input_text: str, history: list[dict] | None = None) -> list[dict]:
        messages = [{"role": "system", "content": agent.system_prompt}]
        messages.extend(history or [])
        messages.append({"role": "user", "content": input_text})
        return messages

    async def execute(
        self, agent: Agent, input_text: str, session_id: UUID, history: list[dict] | None = None
    ) -> ModelResult:
        messages = self.build_messages(agent, input_text, history)
        return await self.gateway.generate(agent.model, messages, session_id)

    async def stream(
        self, agent: Agent, input_text: str, session_id: UUID, history: list[dict] | None = None
    ) -> AsyncIterator[str]:
        messages = self.build_messages(agent, input_text, history)
        async for chunk in self.gateway.stream(agent.model, messages, session_id):
            yield chunk
