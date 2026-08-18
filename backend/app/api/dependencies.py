from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession


async def get_db() -> AsyncIterator[AsyncSession]:
    """Database dependency placeholder used by API routes and test overrides."""
    raise RuntimeError("Database session provider is not configured")
    yield
