"""Modelos de tenant hierárquico: Agency (raiz) → AgencyClient (filho)."""

import uuid
from enum import Enum

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vills.db.base import Base, TimestampMixin


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class Agency(Base, TimestampMixin):
    """Tenant raiz — a agência de marketing."""

    __tablename__ = "agencies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        String(20), default=TenantStatus.ACTIVE, nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    clients: Mapped[list["AgencyClient"]] = relationship(
        back_populates="agency", cascade="all, delete-orphan"
    )


class AgencyClient(Base, TimestampMixin):
    """Tenant filho — um cliente da agência. Tem segmento e tom próprios."""

    __tablename__ = "agency_clients"
    __table_args__ = (
        UniqueConstraint("agency_id", "slug", name="uq_agency_clients_agency_id_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agency_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agencies.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[TenantStatus] = mapped_column(
        String(20), default=TenantStatus.ACTIVE, nullable=False
    )
    segment: Mapped[str] = mapped_column(String(80), nullable=False, default="generico")
    config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    agency: Mapped["Agency"] = relationship(back_populates="clients")
