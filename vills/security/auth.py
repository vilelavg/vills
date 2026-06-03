"""Autenticação JWT: access token curto + refresh token revogável."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from vills.cache.client import get_redis
from vills.core.settings import get_settings

_REVOKED_PREFIX = "revoked_token:"


class TokenError(Exception):
    """Token inválido, expirado ou revogado."""


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: uuid.UUID, agency_slug: str, role: str) -> str:
    settings = get_settings()
    expire = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "agency": agency_slug,
        "role": role,
        "type": "access",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: uuid.UUID, agency_slug: str) -> tuple[str, str]:
    """Retorna (token, jti). O jti é usado para revogação."""
    settings = get_settings()
    jti = str(uuid.uuid4())
    expire = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "agency": agency_slug,
        "type": "refresh",
        "exp": expire,
        "jti": jti,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise TokenError(f"Token inválido: {exc}") from exc


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    """Adiciona o jti à lista de revogados no Redis com TTL."""
    await get_redis().setex(f"{_REVOKED_PREFIX}{jti}", ttl_seconds, "1")


async def is_revoked(jti: str) -> bool:
    return bool(await get_redis().exists(f"{_REVOKED_PREFIX}{jti}"))
