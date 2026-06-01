import importlib
import os

import pytest
from httpx import ASGITransport, AsyncClient


def _clear_env() -> None:
    """Remove env vars que afetam Settings entre testes."""
    prefixes = ("CORS_", "DB_", "LOG_", "DATABASE_", "REDIS_", "ENVIRONMENT", "OTEL_")
    for key in list(os.environ):
        if key.startswith(prefixes):
            os.environ.pop(key, None)


@pytest.fixture
def settings_factory():
    """Recria Settings com env limpo, opcionalmente sobrescrevendo vars."""

    def _make(environment: str = "dev", **env_vars: str):
        _clear_env()
        os.environ["ENVIRONMENT"] = environment
        for key, val in env_vars.items():
            os.environ[key] = val
        from vills.core import settings as settings_mod

        importlib.reload(settings_mod)
        settings_mod.get_settings.cache_clear()
        return settings_mod.Settings()

    yield _make
    _clear_env()


@pytest.fixture
async def client():
    from vills.core.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
