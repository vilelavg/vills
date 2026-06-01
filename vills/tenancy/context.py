"""TenantContext — identifica em nome de quem o Vills está operando."""

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TenantContext:
    """Contexto imutável de uma operação.

    Se client_id é None, a operação é no nível da agência.
    Se preenchido, é no contexto de um cliente específico dela.
    """

    agency_id: uuid.UUID
    agency_slug: str
    agency_config: dict[str, Any] = field(default_factory=dict)

    client_id: uuid.UUID | None = None
    client_slug: str | None = None
    client_segment: str | None = None
    client_config: dict[str, Any] = field(default_factory=dict)

    @property
    def is_client_scope(self) -> bool:
        """True se operando no contexto de um cliente, não da agência."""
        return self.client_id is not None

    @property
    def scope_label(self) -> str:
        """Rótulo legível para logs e traces."""
        if self.is_client_scope:
            return f"{self.agency_slug}/{self.client_slug}"
        return self.agency_slug

    def merged_config(self) -> dict[str, Any]:
        """Config efetiva: agência como base, cliente sobrescreve."""
        merged = dict(self.agency_config)
        if self.is_client_scope:
            merged.update(self.client_config)
        return merged
