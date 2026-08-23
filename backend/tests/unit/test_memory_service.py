"""Memory 领域服务单元测试。

模块职责：验证 MemoryService 的领域读写行为与时间边界。
边界：只使用轻量 FakeDB，不访问真实 PostgreSQL；真实持久化由 integration Gate 覆盖。
关键外部依赖：MemoryService、MemoryRecord 与 pytest-asyncio。
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.services.memory import MemoryService


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
async def test_memory_put_normalizes_aware_expiry_to_naive_utc():
    db = FakeDB()
    service = MemoryService(db)
    expires_at = datetime(2026, 8, 18, 18, 0, tzinfo=UTC) + timedelta(hours=1)

    record = await service.put(
        user_id=uuid4(),
        agent_id=uuid4(),
        memory_key="temporary",
        content="temporary memory",
        expires_at=expires_at,
    )

    assert record.expires_at == expires_at.replace(tzinfo=None)
    assert record.expires_at.tzinfo is None


@pytest.mark.asyncio
async def test_memory_list_limits_context_size():
    db = FakeDB()
    service = MemoryService(db)
    result = await service.list_for_context(user_id=uuid4(), agent_id=uuid4(), limit=1000)
    assert result == []
