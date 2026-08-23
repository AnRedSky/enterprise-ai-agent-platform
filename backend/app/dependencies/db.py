"""HTTP 数据库依赖适配模块。

模块职责：向 FastAPI Handler 提供请求范围内的异步 SQLAlchemy Session。
边界：不创建 Engine、不实现事务策略；数据库连接与 Session 生命周期由 Infrastructure 层负责。
关键依赖：`app.infrastructure.db.get_db_session` 是唯一正式数据库 Session 实现。
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_db_session


async def get_db() -> AsyncIterator[AsyncSession]:
    """提供 API 请求范围内的异步数据库会话。"""
    async for session in get_db_session():
        yield session
