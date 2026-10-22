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
    beat_schedule={
        "blog-tick": {"task": "blog.tick", "schedule": 300.0},
        "seo-indexnow": {"task": "seo.indexnow", "schedule": 3600.0},
        "analytics-dispatch": {"task": "analytics.dispatch", "schedule": 60.0},
    },
)

import app.tasks.analytics  # noqa: E402,F401  (registers "analytics.dispatch")
import app.tasks.blog  # noqa: E402,F401  (registers "blog.tick" / "blog.generate_topic")
import app.tasks.ingest  # noqa: E402,F401  (registers "ingest.document")
import app.tasks.pipeline  # noqa: E402,F401  (registers shared_task "pipeline.run")
import app.tasks.privacy  # noqa: E402,F401  (registers "privacy.delete_user")
import app.tasks.seo  # noqa: E402,F401  (registers "seo.indexnow")
