def test_celery_app_configured():
    from vills.workers.app import celery_app

    assert celery_app.main == "vills"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.task_acks_late is True


def test_health_ping_task_registered():
    from vills.workers.app import celery_app

    assert "vills.health_ping" in celery_app.tasks
