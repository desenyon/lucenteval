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
    # Dead-letter queue config
    task_annotations={
        "app.workers.tasks.run_prompt": {"max_retries": 3, "default_retry_delay": 30},
        "app.workers.tasks.deliver_webhook": {"max_retries": 5},
    },
)
