from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

redis_client: Redis = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=3,
    socket_timeout=3,
    health_check_interval=30,
)
