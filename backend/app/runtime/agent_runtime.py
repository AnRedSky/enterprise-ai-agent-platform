from typing import AsyncIterator
from uuid import UUID

from app.models.agent import Agent
from app.runtime.model_gateway import ModelGateway, ModelResult


class AgentRuntime:
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
