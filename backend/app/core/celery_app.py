import os
from celery import Celery
from app.core.config import settings

# Detect if Redis is available; if not, run tasks synchronously in-process
_redis_available = False
try:
    import redis as _redis_mod
    _r = _redis_mod.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
    _r.ping()
    _redis_available = True
    _r.close()
except Exception:
    _redis_available = False

celery_app = Celery(
    "ai_commerce_worker",
    broker=settings.CELERY_BROKER_URL if _redis_available else None,
    backend=settings.CELERY_RESULT_BACKEND if _redis_available else None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # When Redis is unavailable (local dev), execute tasks synchronously in-process
    task_always_eager=not _redis_available,
    task_eager_propagates=True,
)
