"""RBAC via dependências FastAPI. Resolve auth -> tenant -> papel na ordem certa.

O bloqueio de acesso cross-tenant acontece aqui: um usuário só opera dentro
da própria agência, validado em toda requisição protegida.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from vills.db.session import get_session
from vills.security.auth import TokenError, decode_token, is_revoked
from vills.security.models import AgencyUser
from vills.security.roles import Role
from vills.tenancy.context import TenantContext
from vills.tenancy.resolver import (
    TenantInactiveError,
    TenantNotFoundError,
    TenantResolver,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> AgencyUser:
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token não é de acesso")

    jti = payload.get("jti")
    if jti and await is_revoked(jti):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revogado")

    user_id = uuid.UUID(payload["sub"])
    user = await session.get(AgencyUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inválido")
    return user


async def get_tenant_context(
    agency_slug: str,
    client_slug: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> TenantContext:
    resolver = TenantResolver(session)
    try:
        return await resolver.resolve(agency_slug, client_slug)
    except TenantNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except TenantInactiveError as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(exc)) from exc


def require_role(minimum: Role):
    """Factory de dependência: exige papel mínimo E mesma agência (anti cross-tenant)."""

    async def _checker(
        user: AgencyUser = Depends(get_current_user),
        tenant: TenantContext = Depends(get_tenant_context),
    ) -> AgencyUser:
        if user.agency_id != tenant.agency_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Usuário não pertence a esta agência",
            )
        if not user.role.satisfies(minimum):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requer papel {minimum} ou superior",
            )
        return user

    return _checker
