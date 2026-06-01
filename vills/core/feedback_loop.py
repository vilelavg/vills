"""FeedbackLoop — registra o resultado de cada ação do agente para
aprendizado contínuo. Presente desde a F1, não relegado a fases futuras."""

import uuid
from enum import Enum

from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from vills.db.base import Base, TenantMixin, TimestampMixin
from vills.tenancy.context import TenantContext


class ActionOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    PENDING = "pending"


class ActionLog(Base, TenantMixin, TimestampMixin):
    """Registro imutável de cada ação do agente e seu resultado."""

    __tablename__ = "action_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), index=True, nullable=True
    )
    module: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome: Mapped[ActionOutcome] = mapped_column(
        String(20), default=ActionOutcome.PENDING, nullable=False
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FeedbackLoop:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        tenant: TenantContext,
        module: str,
        action: str,
        outcome: ActionOutcome = ActionOutcome.PENDING,
        score: float | None = None,
        details: dict | None = None,
        notes: str | None = None,
    ) -> ActionLog:
        if score is not None and not 0.0 <= score <= 1.0:
            raise ValueError(f"score deve estar entre 0.0 e 1.0, recebido {score}")

        entry = ActionLog(
            tenant_id=tenant.agency_id,
            client_id=tenant.client_id,
            module=module,
            action=action,
            outcome=outcome,
            score=score,
            details=details or {},
            notes=notes,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry
