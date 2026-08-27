"""Workflow transaction ownership primitives.

The workflow domain services may participate in a caller-owned transaction.  This
module keeps transaction ownership explicit instead of letting lower-level domain
operations accidentally commit or roll back the caller's transaction.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def nested_write(db: AsyncSession) -> AsyncIterator[None]:
    """Run a contention-prone durable write inside a SAVEPOINT.

    The caller retains ownership of the outer transaction.  An integrity failure
    rolls back only the nested transaction, allowing the caller to inspect the
    conflicting durable row and continue without losing earlier work.
    """
    async with db.begin_nested():
        yield


async def commit_owned(db: AsyncSession, *, owned: bool) -> None:
    """Commit only when the current service invocation owns the transaction."""
    if owned:
        await db.commit()
