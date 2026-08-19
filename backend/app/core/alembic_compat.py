from sqlalchemy import text


async def prepare_alembic_version_table(connection) -> None:
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
