"""pgvector storage for knowledge chunk embeddings

Revision ID: 0010_pgvector_knowledge_chunks
Revises: 0009_agent_knowledge_config
"""
from alembic import op
from app.core.config import settings

revision = "0010_pgvector_knowledge_chunks"
down_revision = "0009_agent_knowledge_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dimension = int(settings.embedding_dimension)
    if dimension < 1:
        raise ValueError("EMBEDDING_DIMENSION must be greater than zero")

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE knowledge_chunks (
            chunk_id uuid PRIMARY KEY
                REFERENCES knowledge_document_chunks(id) ON DELETE CASCADE,
            knowledge_base_id uuid NOT NULL
                REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            document_version_id uuid NOT NULL
                REFERENCES knowledge_document_versions(id) ON DELETE CASCADE,
            embedding vector({dimension}) NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_knowledge_base_id "
        "ON knowledge_chunks (knowledge_base_id)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_document_version_id "
        "ON knowledge_chunks (document_version_id)"
    )
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_hnsw "
        "ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_document_version_id")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_knowledge_base_id")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks")
