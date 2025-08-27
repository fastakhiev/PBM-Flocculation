import aioredis
from app.core import config

redis_async = aioredis.from_url(f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}", decode_responses=True)
