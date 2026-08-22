"""Add isolated variable-dimension storage for retrieval evaluation vectors.

Revision ID: 0027_retrieval_evaluation_vector_space
Revises: 0026_model_profile_runtime_identity
"""
from alembic import op

revision = "0027_retrieval_evaluation_vector_space"
down_revision = "0026_model_profile_runtime_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE retrieval_evaluation_vectors (
            chunk_id uuid NOT NULL
                REFERENCES knowledge_document_chunks(id) ON DELETE CASCADE,
            knowledge_base_id uuid NOT NULL
                REFERENCES knowledge_bases(id) ON DELETE CASCADE,
            embedding_dimension integer NOT NULL CHECK (embedding_dimension > 0),
            embedding vector NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (knowledge_base_id, embedding_dimension, chunk_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_retrieval_evaluation_vectors_scope "
        "ON retrieval_evaluation_vectors (knowledge_base_id, embedding_dimension)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_retrieval_evaluation_vectors_scope")
    op.execute("DROP TABLE IF EXISTS retrieval_evaluation_vectors")
