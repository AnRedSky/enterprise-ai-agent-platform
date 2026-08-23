"""Memory 领域业务服务。

模块职责：负责 MemoryRecord 的写入、读取、更新、删除、上下文列表与文本检索。
边界：只处理 Memory 领域规则，不负责 HTTP 协议、Runtime 编排或数据库 Session 创建。
关键外部依赖：SQLAlchemy AsyncSession 与 MemoryRecord ORM 模型；时间字段按 PostgreSQL TIMESTAMP WITHOUT TIME ZONE 的朴素 UTC 约定落库。
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryRecord


class MemoryNotFoundError(Exception):
    """Memory 记录不存在或不属于当前用户与 Agent 范围。"""


class MemoryService:
    """封装 Memory 的领域读写规则与租户/主体范围约束。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _utc_naive(value: datetime | None) -> datetime | None:
        """将时间归一为朴素 UTC，匹配 PostgreSQL 无时区时间列。"""
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    @classmethod
    def _visible_clause(cls):
        """构造当前仍有效的 Memory 可见性条件。"""
        now = datetime.now(UTC).replace(tzinfo=None)
        return and_(
            MemoryRecord.is_active.is_(True),
            or_(MemoryRecord.expires_at.is_(None), MemoryRecord.expires_at > now),
        )

    async def put(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
        memory_key: str,
        content: str,
        memory_type: str = "fact",
        session_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            memory_type=memory_type,
            memory_key=memory_key,
            content=content,
            expires_at=self._utc_naive(expires_at),
            is_active=True,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get(self, *, user_id: UUID, agent_id: UUID, memory_id: UUID) -> MemoryRecord:
        result = await self.db.execute(
            select(MemoryRecord).where(
                MemoryRecord.id == memory_id,
                MemoryRecord.user_id == user_id,
                MemoryRecord.agent_id == agent_id,
                self._visible_clause(),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise MemoryNotFoundError("Memory not found")
        return record

    async def update(
        self,
        *,
        user_id: UUID,
        agent_id: UUID,
        memory_id: UUID,
        memory_key: str | None = None,
        content: str | None = None,
        memory_type: str | None = None,
        expires_at: datetime | None = None,
        is_active: bool | None = None,
    ) -> MemoryRecord:
        record = await self.get(user_id=user_id, agent_id=agent_id, memory_id=memory_id)
        if memory_key is not None:
            record.memory_key = memory_key
        if content is not None:
            record.content = content
        if memory_type is not None:
            record.memory_type = memory_type
        if expires_at is not None:
            record.expires_at = self._utc_naive(expires_at)
        if is_active is not None:
            record.is_active = is_active
        await self.db.flush()
        return record

    async def delete(self, *, user_id: UUID, agent_id: UUID, memory_id: UUID) -> None:
        record = await self.get(user_id=user_id, agent_id=agent_id, memory_id=memory_id)
        await self.db.delete(record)
        await self.db.flush()

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
            self._visible_clause(),
        )
        if session_id is not None:
            query = query.where((MemoryRecord.session_id == session_id) | (MemoryRecord.session_id.is_(None)))
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
                self._visible_clause(),
            )
            .order_by(MemoryRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
