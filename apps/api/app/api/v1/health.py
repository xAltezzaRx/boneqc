import asyncio
import time
from datetime import datetime, timezone

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.database.session import engine
from app.queue.client import redis_client
from app.queue.heartbeat import (
    WORKER_HEARTBEAT_KEY,
    WORKER_HEARTBEAT_TTL_SECONDS,
)
from app.storage.service import storage

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    settings = get_settings()

    return {
        "status": "ok",
        "service": settings.service_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/live")
def live() -> dict:
    return {"status": "alive"}


@router.get("/health/ready")
async def ready() -> dict:
    dependencies = {
        "database": "unknown",
        "object_storage": "unknown",
        "redis": "unknown",
        "worker": "unknown",
    }

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        dependencies["database"] = "ok"

    except (SQLAlchemyError, OSError, TimeoutError) as exc:
        dependencies["database"] = "unavailable"

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        ) from exc

    try:
        await asyncio.to_thread(storage.healthcheck)
        dependencies["object_storage"] = "ok"

    except (BotoCoreError, ClientError, OSError, TimeoutError) as exc:
        dependencies["object_storage"] = "unavailable"

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        ) from exc

    try:
        await redis_client.ping()
        dependencies["redis"] = "ok"

    except (RedisError, OSError, TimeoutError) as exc:
        dependencies["redis"] = "unavailable"

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        ) from exc

    try:
        raw_heartbeat = await redis_client.get(
            WORKER_HEARTBEAT_KEY
        )

        if raw_heartbeat is None:
            dependencies["worker"] = "unavailable"

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "dependencies": dependencies,
                },
            )

        heartbeat_age = (
            time.time() - float(raw_heartbeat)
        )

        if (
            heartbeat_age < 0
            or heartbeat_age
            > WORKER_HEARTBEAT_TTL_SECONDS
        ):
            dependencies["worker"] = "unavailable"

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "not_ready",
                    "dependencies": dependencies,
                },
            )

        dependencies["worker"] = "ok"

    except HTTPException:
        raise

    except (
        RedisError,
        ValueError,
        TypeError,
        OSError,
        TimeoutError,
    ) as exc:
        dependencies["worker"] = "unavailable"

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "dependencies": dependencies,
            },
        ) from exc

    return {
        "status": "ready",
        "dependencies": dependencies,
    }
