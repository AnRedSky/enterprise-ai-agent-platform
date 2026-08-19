"""track knowledge vector indexing state

Revision ID: 0011_knowledge_vector_index_status
Revises: 0010_pgvector_knowledge_chunks
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_knowledge_vector_index_status"
down_revision = "0010_pgvector_knowledge_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_document_versions",
        sa.Column("vector_index_status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.add_column(
        "knowledge_document_versions",
        sa.Column("embedding_model", sa.String(200), nullable=True),
    )
    op.create_index(
        "ix_knowledge_document_versions_vector_index_status",
        "knowledge_document_versions",
        ["vector_index_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_document_versions_vector_index_status", table_name="knowledge_document_versions")
    op.drop_column("knowledge_document_versions", "embedding_model")
    op.drop_column("knowledge_document_versions", "vector_index_status")
