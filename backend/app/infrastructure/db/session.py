"""SQLAlchemy 数据库会话基础设施。"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import registry as _model_registry  # noqa: F401


engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session():
    """创建一个请求范围内的数据库会话。"""
    async with SessionLocal() as session:
        yield session
