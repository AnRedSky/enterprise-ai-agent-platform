"""HTTP 依赖适配模块：集中暴露 API 层需要的请求上下文依赖。

边界：只负责 FastAPI 依赖注入适配，不实现数据库连接或业务规则。
关键依赖：`app.infrastructure.db` 提供唯一正式数据库 Session 实现。
"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_db as _get_db


async def get_db() -> AsyncIterator[AsyncSession]:
    """提供 API 请求范围内的异步数据库会话。"""
    async for session in _get_db():
        yield session
