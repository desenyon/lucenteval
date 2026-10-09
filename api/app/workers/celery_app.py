from celery import Celery

from ..core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lucenteval",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.workers.tasks.run_prompt": {"queue": "runner"},
        "app.workers.tasks.score_result": {"queue": "scorer"},
        "app.workers.tasks.deliver_webhook": {"queue": "webhook"},
    },
    task_queues={
        "runner": {"exchange": "runner", "routing_key": "runner"},
        "scorer": {"exchange": "scorer", "routing_key": "scorer"},
        "webhook": {"exchange": "webhook", "routing_key": "webhook"},
    },
    worker_prefetch_multiplier=1,
    task_publish_retry=False,
    broker_connection_timeout=3,
    task_ignore_result=True,
    beat_schedule={
        "reconcile-durable-work": {
            "task": "app.workers.tasks.reconcile_work",
            "schedule": 30.0,
            "options": {"queue": "runner"},
        },
    },
)
