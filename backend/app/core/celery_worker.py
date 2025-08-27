from celery import Celery
from app.core import config

celery = Celery(
"tasks", broker=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/1", backend=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/0"
)
