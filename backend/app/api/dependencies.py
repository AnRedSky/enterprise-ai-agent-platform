from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db as _get_db


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield the application's async database session.

    Kept in the API layer so tests and routes can override this dependency
    without importing the infrastructure module directly.
    """
    async for session in _get_db():
        yield session
