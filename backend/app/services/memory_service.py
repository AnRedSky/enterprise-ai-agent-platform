from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryRecord


class MemoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def put(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
        memory_key: str,
        content: str,
        memory_type: str = "fact",
        session_id: UUID | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            memory_key=memory_key,
            content=content,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_for_context(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
        session_id: UUID | None = None,
        limit: int = 20,
    ) -> list[MemoryRecord]:
        limit = max(1, min(limit, 100))
        query = select(MemoryRecord).where(
            MemoryRecord.user_id == user_id,
            MemoryRecord.agent_id == agent_id,
        )
        if session_id is not None:
            query = query.where(
                (MemoryRecord.session_id == session_id) | (MemoryRecord.session_id.is_(None))
            )
        query = query.order_by(MemoryRecord.created_at.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
        query_text: str,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        limit = max(1, min(limit, 50))
        pattern = f"%{query_text.strip()}%"
        result = await self.db.execute(
            select(MemoryRecord)
            .where(
                MemoryRecord.user_id == user_id,
                MemoryRecord.agent_id == agent_id,
                MemoryRecord.content.ilike(pattern),
            )
            .order_by(MemoryRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
