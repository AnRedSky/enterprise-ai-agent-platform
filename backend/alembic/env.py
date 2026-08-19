from logging.config import fileConfig
import asyncio

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.models.core import Base
from app.models.execution import Execution, ExecutionEvent  # noqa: F401
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentVersion  # noqa: F401
from app.models.workflow import Workflow, WorkflowVersion  # noqa: F401
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution  # noqa: F401


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

# Keep Alembic and the application on the same DATABASE_URL/.env configuration.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def _prepare_alembic_version_table(connection) -> None:
    """Keep legacy Alembic metadata compatible with longer revision ids.

    The project historically created alembic_version.version_num as VARCHAR(32),
    while current revision ids may exceed that length. The preflight is safe for
    existing databases and is intentionally a no-op before the Alembic version
    table exists on a brand-new database.
    """
    exists = await connection.scalar(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'alembic_version'
            )
            """
        )
    )
    if not exists:
        return

    length = await connection.scalar(
        text(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'alembic_version'
              AND column_name = 'version_num'
            """
        )
    )
    if length is not None and length < 64:
        await connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(64)"
            )
        )


async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await _prepare_alembic_version_table(connection)
        await connection.run_sync(
            lambda c: context.configure(connection=c, target_metadata=target_metadata)
        )
        async with connection.begin():
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
