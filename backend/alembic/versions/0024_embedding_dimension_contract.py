"""Reconcile pgvector embedding dimension with the configured provider contract.

Revision ID: 0024_embedding_dimension_contract
Revises: 0023_organization_membership
"""
from alembic import op
from app.core.config import settings

revision = "0024_embedding_dimension_contract"
down_revision = "0023_organization_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dimension = int(settings.embedding_dimension)
    if dimension < 1:
        raise ValueError("EMBEDDING_DIMENSION must be greater than zero")

    # knowledge_chunks is a derived vector cache: source chunks remain intact
    # and can always be re-embedded. When the configured provider changes
    # dimension, invalidate that cache before changing the pgvector typmod.
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("TRUNCATE TABLE knowledge_chunks")
    op.execute(
        f"ALTER TABLE knowledge_chunks "
        f"ALTER COLUMN embedding TYPE vector({dimension}) "
        f"USING embedding::vector({dimension})"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    # The previous migration also derives its dimension from configuration.
    # Reversing this migration therefore restores the configured dimension at
    # the time downgrade is executed and invalidates the derived vector cache.
    dimension = int(settings.embedding_dimension)
    if dimension < 1:
        raise ValueError("EMBEDDING_DIMENSION must be greater than zero")

    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("TRUNCATE TABLE knowledge_chunks")
    op.execute(
        f"ALTER TABLE knowledge_chunks "
        f"ALTER COLUMN embedding TYPE vector({dimension}) "
        f"USING embedding::vector({dimension})"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )
