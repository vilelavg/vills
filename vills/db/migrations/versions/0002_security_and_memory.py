"""seguranca, auditoria e memoria vetorial

Cria agency_users, audit_logs e memory_chunks.
Habilita as extensoes vector e pg_trgm ANTES das tabelas que as usam (R3).

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    # Extensoes primeiro — IF NOT EXISTS e seguro em re-runs (R3)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "agency_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agency_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False),
        sa.Column("mfa_secret", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agency_id"],
            ["agencies.id"],
            ondelete="CASCADE",
            name="fk_agency_users_agency_id_agencies",
        ),
        sa.UniqueConstraint(
            "agency_id", "email", name="uq_agency_users_agency_id_email"
        ),
    )
    op.create_index("ix_agency_users_agency_id", "agency_users", ["agency_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=True),
        sa.Column("resource_id", sa.String(120), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    op.create_table(
        "memory_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_chunks_tenant_id", "memory_chunks", ["tenant_id"])
    op.create_index("ix_memory_chunks_client_id", "memory_chunks", ["client_id"])
    # indice trigram para busca lexical (BM25-like) no conteudo
    op.execute(
        "CREATE INDEX ix_memory_chunks_content_trgm ON memory_chunks "
        "USING gin (content gin_trgm_ops)"
    )


def downgrade() -> None:
    op.drop_table("memory_chunks")
    op.drop_index("ix_audit_logs_action", "audit_logs")
    op.drop_index("ix_audit_logs_actor_id", "audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", "audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_agency_users_agency_id", "agency_users")
    op.drop_table("agency_users")
    # extensoes nao sao removidas — podem ser usadas por outros recursos
