from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.core import Base
DATABASE_URL = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
async def get_db():
    async with SessionLocal() as session: yield session
