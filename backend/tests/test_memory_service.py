from uuid import uuid4

import pytest

from app.services.memory_service import MemoryService


class FakeResult:
    def scalars(self):
        return self

    def all(self):
        return []


class FakeDB:
    def add(self, obj):
        self.obj = obj

    async def flush(self):
        return None

    async def execute(self, query):
        self.query = query
        return FakeResult()


@pytest.mark.asyncio
async def test_memory_put_creates_record():
    db = FakeDB()
    service = MemoryService(db)
    record = await service.put(
        user_id=uuid4(),
        agent_id=uuid4(),
        memory_key="language",
        content="User prefers Chinese.",
    )
    assert record.memory_type == "fact"
    assert record.memory_key == "language"
    assert record.content == "User prefers Chinese."


@pytest.mark.asyncio
async def test_memory_list_limits_context_size():
    db = FakeDB()
    service = MemoryService(db)
    result = await service.list_for_context(user_id=uuid4(), agent_id=uuid4(), limit=1000)
    assert result == []
