import asyncio
import logging
import time

from redis.exceptions import RedisError

from app.queue.client import redis_client


logger = logging.getLogger("boneqc.worker.heartbeat")

WORKER_HEARTBEAT_KEY = "boneqc:worker:heartbeat"
WORKER_HEARTBEAT_INTERVAL_SECONDS = 5
WORKER_HEARTBEAT_TTL_SECONDS = 20


async def publish_worker_heartbeat() -> None:
    await redis_client.set(
        WORKER_HEARTBEAT_KEY,
        f"{time.time():.6f}",
        ex=WORKER_HEARTBEAT_TTL_SECONDS,
    )


async def run_worker_heartbeat() -> None:
    while True:
        try:
            await publish_worker_heartbeat()

        except RedisError:
            logger.exception(
                "worker_heartbeat_failed"
            )

        await asyncio.sleep(
            WORKER_HEARTBEAT_INTERVAL_SECONDS
        )
