"""Cliente Redis assíncrono."""

import asyncio

import redis.asyncio as aioredis

from vills.core.settings import get_settings

_client: aioredis.Redis | None = None

PING_TIMEOUT = 3.0


def init_redis() -> aioredis.Redis:
    global _client
    if _client is None:
        settings = get_settings()
        _client = aioredis.from_url(
            settings.redis_url.get_secret_value(),
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


def get_redis() -> aioredis.Redis:
    return _client if _client is not None else init_redis()


async def ping_redis() -> bool:
    try:
        async with asyncio.timeout(PING_TIMEOUT):
            return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001
        return False


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
