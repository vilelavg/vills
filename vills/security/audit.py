"""Audit log append-only. Registra quem fez o quê, quando, em qual tenant.

Nunca atualizado, nunca deletado — requisito de LGPD e rastreabilidade.
"""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from vills.db.base import Base, TenantMixin, TimestampMixin


class AuditLog(Base, TenantMixin, TimestampMixin):
    """Registro imutável de ação relevante para auditoria."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # quem: id do usuário (None se ação do sistema)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=True
    )
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # o quê: ação realizada (ex: "user.login", "campaign.create")
    action: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    # sobre o quê: tipo e id do recurso afetado
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # contexto adicional
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, default=dict, nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLogger:
    """Escreve entradas de auditoria. Nunca lê para alterar — só append."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        tenant_id: uuid.UUID,
        action: str,
        actor_id: uuid.UUID | None = None,
        actor_email: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        notes: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_=metadata or {},
            ip_address=ip_address,
            notes=notes,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
