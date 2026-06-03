"""Papéis de acesso (RBAC). Hierarquia: admin > operator > viewer."""

from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

    @property
    def rank(self) -> int:
        """Nível hierárquico para comparação. Maior = mais permissões."""
        return {Role.VIEWER: 1, Role.OPERATOR: 2, Role.ADMIN: 3}[self]

    def satisfies(self, required: "Role") -> bool:
        """True se este papel atende ao papel mínimo exigido."""
        return self.rank >= required.rank
