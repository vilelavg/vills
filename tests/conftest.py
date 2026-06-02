import importlib
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


def _load_dotenv() -> None:
    """Carrega o .env da raiz do projeto se existir.
    Garante que DATABASE_URL e REDIS_URL chegam aos testes mesmo no Windows,
    onde o pytest não herda variáveis do .env automaticamente.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    with env_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ[key] = value


# Carrega o .env logo que o conftest é importado
_load_dotenv()


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


@pytest_asyncio.fixture
async def db_session():
    """Sessão de banco para os testes da F1.

    Carrega DATABASE_URL do .env (via _load_dotenv acima) ou do ambiente.
    Se não houver Postgres acessível, o teste é pulado com mensagem clara.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from vills.core import feedback_loop  # noqa: F401 — registra action_logs
    from vills.db.base import Base
    from vills.tenancy import models  # noqa: F401 — registra tabelas

    # Recarrega o .env porque settings_factory/_clear_env pode ter removido DATABASE_URL
    _load_dotenv()
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://vills:vills@localhost:5432/vills")
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"Postgres indisponível para teste de integração: {exc}")

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
