"""knowledge registry

Revision ID: 0007_knowledge_registry
Revises: 0006_agent_lifecycle
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_knowledge_registry"
down_revision = "0006_agent_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_base_owner_status", "knowledge_bases", ["owner_id", "status"])
    op.create_index("ix_knowledge_bases_owner_id", "knowledge_bases", ["owner_id"])
    op.create_index("ix_knowledge_bases_status", "knowledge_bases", ["status"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_document_kb_status", "knowledge_documents", ["knowledge_base_id", "status"])
    op.create_index("ix_knowledge_documents_knowledge_base_id", "knowledge_documents", ["knowledge_base_id"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])

    op.create_table(
        "knowledge_document_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("source_uri", sa.String(length=1000), nullable=True),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "version", name="uq_knowledge_document_version"),
    )
    op.create_index("ix_knowledge_document_versions_document_id", "knowledge_document_versions", ["document_id"])
    op.create_index("ix_knowledge_document_versions_status", "knowledge_document_versions", ["status"])
    op.create_index("ix_knowledge_document_versions_created_by", "knowledge_document_versions", ["created_by"])

    op.create_foreign_key(
        "fk_knowledge_document_current_version",
        "knowledge_documents",
        "knowledge_document_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_knowledge_document_current_version", "knowledge_documents", type_="foreignkey")
    op.drop_index("ix_knowledge_document_versions_created_by", table_name="knowledge_document_versions")
    op.drop_index("ix_knowledge_document_versions_status", table_name="knowledge_document_versions")
    op.drop_index("ix_knowledge_document_versions_document_id", table_name="knowledge_document_versions")
    op.drop_table("knowledge_document_versions")
    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_knowledge_base_id", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_document_kb_status", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
    op.drop_index("ix_knowledge_bases_status", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_bases_owner_id", table_name="knowledge_bases")
    op.drop_index("ix_knowledge_base_owner_status", table_name="knowledge_bases")
    op.drop_table("knowledge_bases")
