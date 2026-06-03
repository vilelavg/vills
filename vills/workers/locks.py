"""Lock distribuído via Redis para idempotência de jobs.

Garante que um job agendado não rode em paralelo em múltiplas instâncias —
resolve o problema de jobs duplicados do APScheduler do Villa.
"""

import contextlib
from collections.abc import AsyncGenerator

from vills.cache.client import get_redis

_LOCK_PREFIX = "job_lock:"


@contextlib.asynccontextmanager
async def distributed_lock(
    name: str, ttl_seconds: int = 300
) -> AsyncGenerator[bool, None]:
    """Adquire um lock nomeado. Cede True se conseguiu, False se já estava preso.

    Uso:
        async with distributed_lock("daily_report") as acquired:
            if acquired:
                ...  # só uma instância executa
    """
    redis = get_redis()
    key = f"{_LOCK_PREFIX}{name}"
    # SET NX EX: só seta se não existir, com expiração (auto-libera se travar)
    acquired = await redis.set(key, "1", nx=True, ex=ttl_seconds)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await redis.delete(key)
