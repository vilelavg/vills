"""Tasks assíncronas do Celery.

As tasks são síncronas do ponto de vista do Celery, mas chamam código async
via asyncio.run quando necessário. Tasks pesadas (relatórios, sync de ads)
ficam aqui, fora do request/response do FastAPI.
"""

from vills.observability.logging import get_logger
from vills.workers.app import celery_app

log = get_logger(__name__)


@celery_app.task(name="vills.health_ping")
def health_ping() -> str:
    """Task trivial para validar que o worker está processando a fila."""
    log.info("worker_health_ping")
    return "pong"
