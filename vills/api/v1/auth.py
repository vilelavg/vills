"""Endpoints de autenticação: login, refresh, logout, MFA."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vills.db.session import get_session
from vills.security.auth import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
)
from vills.security.models import AgencyUser
from vills.security.passwords import verify_password
from vills.tenancy.models import Agency

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "vills_refresh"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


async def _find_user(
    session: AsyncSession, agency_slug: str, email: str
) -> AgencyUser | None:
    result = await session.execute(
        select(AgencyUser)
        .join(Agency, AgencyUser.agency_id == Agency.id)
        .where(Agency.slug == agency_slug, AgencyUser.email == email)
    )
    return result.scalar_one_or_none()


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    agency_slug: str,
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    user = await _find_user(session, agency_slug, form.username)
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuário inativo")

    access = create_access_token(user.id, agency_slug, user.role)
    refresh, _jti = create_refresh_token(user.id, agency_slug)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        httponly=True,
        samesite="strict",
        secure=True,
    )
    return TokenResponse(access_token=access)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token_endpoint(
    response: Response,
    vills_refresh: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    if not vills_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sem refresh token")
    try:
        payload = decode_token(vills_refresh)
    except TokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token não é refresh")

    user_id = uuid.UUID(payload["sub"])
    user = await session.get(AgencyUser, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário inválido")

    access = create_access_token(user.id, payload["agency"], user.role)
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    vills_refresh: str | None = None,
) -> None:
    """Revoga o refresh token e limpa o cookie."""
    if vills_refresh:
        try:
            payload = decode_token(vills_refresh)
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                ttl = max(int(exp - datetime.now(UTC).timestamp()), 1)
                await revoke_token(jti, ttl)
        except TokenError:
            pass  # token já inválido, nada a revogar
    response.delete_cookie(REFRESH_COOKIE)
