import json
from uuid import UUID

from app.queue.client import redis_client


ANALYSIS_QUEUE = "boneqc:analysis:jobs"
ANALYSIS_DEAD_QUEUE = "boneqc:analysis:dead"

MAX_ANALYSIS_ATTEMPTS = 3
ANALYSIS_RETRY_DELAY_SECONDS = 2


def build_analysis_payload(
    *,
    job_id: UUID,
    study_id: UUID,
) -> str:
    return json.dumps(
        {
            "job_id": str(job_id),
            "study_id": str(study_id),
        }
    )


async def enqueue_analysis_job(
    *,
    job_id: UUID,
    study_id: UUID,
) -> None:
    await redis_client.rpush(
        ANALYSIS_QUEUE,
        build_analysis_payload(
            job_id=job_id,
            study_id=study_id,
        ),
    )


async def enqueue_dead_letter(
    *,
    job_id: UUID,
    study_id: UUID,
    attempts: int,
    error_message: str,
    failure_type: str,
) -> None:
    payload = {
        "job_id": str(job_id),
        "study_id": str(study_id),
        "attempts": attempts,
        "error_message": error_message[:2000],
        "failure_type": failure_type,
    }

    await redis_client.rpush(
        ANALYSIS_DEAD_QUEUE,
        json.dumps(payload),
    )


async def count_dead_letters() -> int:
    return int(
        await redis_client.llen(
            ANALYSIS_DEAD_QUEUE
        )
    )


async def list_dead_letters(
    *,
    offset: int = 0,
    limit: int = 100,
) -> list[dict]:
    stop = offset + limit - 1

    raw_items = await redis_client.lrange(
        ANALYSIS_DEAD_QUEUE,
        offset,
        stop,
    )

    items: list[dict] = []

    for raw in raw_items:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        if isinstance(payload, dict):
            items.append(payload)

    return items


async def requeue_analysis_job(
    *,
    job_id: UUID,
    study_id: UUID,
) -> int:
    raw_items = await redis_client.lrange(
        ANALYSIS_DEAD_QUEUE,
        0,
        -1,
    )

    matching_dead_letters: list[str] = []

    for raw in raw_items:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue

        if (
            isinstance(payload, dict)
            and payload.get("job_id") == str(job_id)
        ):
            matching_dead_letters.append(raw)

    pipeline = redis_client.pipeline(
        transaction=True
    )

    pipeline.rpush(
        ANALYSIS_QUEUE,
        build_analysis_payload(
            job_id=job_id,
            study_id=study_id,
        ),
    )

    for raw in matching_dead_letters:
        pipeline.lrem(
            ANALYSIS_DEAD_QUEUE,
            0,
            raw,
        )

    results = await pipeline.execute()

    removed = 0

    for result in results[1:]:
        removed += int(result)

    return removed
