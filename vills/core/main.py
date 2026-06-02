"""Ponto de entrada da API do Vills."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vills.api.v1.health import router as health_router
from vills.cache.client import close_redis, init_redis
from vills.core.settings import get_settings
from vills.db.session import dispose_engine, init_engine
from vills.observability.logging import configure_logging, get_logger
from vills.observability.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = get_logger(__name__)
    settings = get_settings()
    init_engine()
    init_redis()
    log.info("vills_starting", config=settings.safe_dump())
    yield
    await dispose_engine()
    await close_redis()
    log.info("vills_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title="Vills", version="0.1.0", debug=settings.debug, lifespan=lifespan)

    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router, prefix=settings.api_v1_prefix)
    configure_tracing(app)
    return app


app = create_app()
