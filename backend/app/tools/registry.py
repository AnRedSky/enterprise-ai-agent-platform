from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict

class Tool(ABC):
    spec: ToolSpec
    @abstractmethod
    async def execute(self, arguments: dict) -> dict: ...

class ToolRegistry:
    def __init__(self): self._tools: dict[str, Tool] = {}
    def register(self, tool: Tool): self._tools[tool.spec.name] = tool
    def get(self, name: str): return self._tools.get(name)
    def list(self): return [x.spec for x in self._tools.values()]
