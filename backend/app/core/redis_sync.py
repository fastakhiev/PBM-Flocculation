import redis
from app.core import config

redis_sync = redis.Redis(
    host=config.REDIS_HOST, port=6379, db=0
)
