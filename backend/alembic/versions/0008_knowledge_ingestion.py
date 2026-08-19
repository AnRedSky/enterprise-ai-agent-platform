"""knowledge ingestion chunks

Revision ID: 0008_knowledge_ingestion
Revises: 0007_knowledge_registry
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_knowledge_ingestion"
down_revision = "0007_knowledge_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "knowledge_document_versions",
        sa.Column("ingestion_status", sa.String(length=20), nullable=False, server_default="pending"),
    )
    op.create_index(
        "ix_knowledge_document_versions_ingestion_status",
        "knowledge_document_versions",
        ["ingestion_status"],
    )
    op.create_table(
        "knowledge_document_chunks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_version_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_version_id"], ["knowledge_document_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_version_id", "chunk_index", name="uq_knowledge_document_chunk_index"),
    )
    op.create_index(
        "ix_knowledge_document_chunks_version_index",
        "knowledge_document_chunks",
        ["document_version_id", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_index("ix_knowledge_document_chunks_version_index", table_name="knowledge_document_chunks")
    op.drop_table("knowledge_document_chunks")
    op.drop_index("ix_knowledge_document_versions_ingestion_status", table_name="knowledge_document_versions")
    op.drop_column("knowledge_document_versions", "ingestion_status")
