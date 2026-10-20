"""Celery app."""
from celery import Celery

from app.config import settings

celery_app = Celery(
    "crowdscope",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    worker_max_tasks_per_child=20,
    task_time_limit=3600 * 3,
    task_soft_time_limit=3600 * 3 - 60,
)

import app.tasks.ingest  # noqa: E402,F401  (registers "ingest.document")
import app.tasks.pipeline  # noqa: E402,F401  (registers shared_task "pipeline.run")
