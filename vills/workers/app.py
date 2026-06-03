"""Aplicação Celery. Broker e backend no Redis.

Em produção (Linux/EKS) usa o pool prefork padrão. Em dev no Windows,
o worker roda no container Linux do docker-compose, evitando a limitação
de multiprocessing do Windows.
"""

from celery import Celery

from vills.core.settings import get_settings


def create_celery() -> Celery:
    settings = get_settings()
    broker = settings.celery_broker_url.get_secret_value()
    app = Celery("vills", broker=broker, backend=broker)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,  # task só é confirmada após concluir (resiliência)
        worker_prefetch_multiplier=1,
    )
    app.autodiscover_tasks(["vills.workers"])
    return app


celery_app = create_celery()

# Importa as tasks para registro imediato (autodiscover é lazy — só no worker).
# Import ao final evita import circular com tasks.py, que importa celery_app.
from vills.workers import tasks  # noqa: E402,F401
