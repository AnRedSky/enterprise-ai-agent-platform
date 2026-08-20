from logging.config import fileConfig
import asyncio

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.alembic_compat import prepare_alembic_version_table
from app.core.config import settings
from app.models.core import Base
from app.models.execution import Execution, ExecutionEvent  # noqa: F401
from app.models.knowledge import KnowledgeBase, KnowledgeDocument, KnowledgeDocumentVersion  # noqa: F401
from app.models.workflow import Workflow, WorkflowVersion  # noqa: F401
from app.models.workflow_circuit import WorkflowCircuitState  # noqa: F401
from app.models.workflow_execution import WorkflowExecution, WorkflowNodeExecution  # noqa: F401
from app.models.workflow_trace import WorkflowTraceEvent  # noqa: F401
from app.models.workflow_trigger import WorkflowTrigger  # noqa: F401

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    connectable = async_engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.",
                                           poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        async with connection.begin():
            await prepare_alembic_version_table(connection)
            await connection.run_sync(lambda c: context.configure(connection=c, target_metadata=target_metadata))
            await connection.run_sync(lambda _: context.run_migrations())
    await connectable.dispose()


def run_migrations_online():
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
