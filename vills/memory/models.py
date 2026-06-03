"""Modelo de chunk de memória com embedding vetorial (pgvector)."""

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vills.db.base import Base, TenantMixin, TimestampMixin

# Dimensão do embedding. text-embedding-3-small = 1536.
EMBEDDING_DIM = 1536


class MemoryChunk(Base, TenantMixin, TimestampMixin):
    """Pedaço de conhecimento indexado para RAG, isolado por tenant."""

    __tablename__ = "memory_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # client_id None = conhecimento da agência; preenchido = de um cliente
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=True
    )
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
