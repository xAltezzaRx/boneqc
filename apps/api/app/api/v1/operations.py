from fastapi import Depends
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError
from redis.exceptions import RedisError

from app.auth.security import require_roles
from app.models.enums import UserRole
from app.queue.service import (
    count_dead_letters,
    list_dead_letters,
)
from app.schemas.operations import (
    DeadLetterCountResponse,
    DeadLetterEntry,
    DeadLetterListResponse,
)


router = APIRouter(
    prefix="/operations",
    tags=["operations"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


@router.get(
    "/dead-letter/count",
    response_model=DeadLetterCountResponse,
)
async def get_dead_letter_count() -> DeadLetterCountResponse:
    try:
        count = await count_dead_letters()

    except (RedisError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QUEUE_UNAVAILABLE"},
        ) from exc

    return DeadLetterCountResponse(
        count=count,
    )


@router.get(
    "/dead-letter",
    response_model=DeadLetterListResponse,
)
async def get_dead_letters(
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> DeadLetterListResponse:
    try:
        total = await count_dead_letters()

        raw_items = await list_dead_letters(
            offset=offset,
            limit=limit,
        )

    except (RedisError, OSError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QUEUE_UNAVAILABLE"},
        ) from exc

    items: list[DeadLetterEntry] = []

    for raw in raw_items:
        try:
            items.append(
                DeadLetterEntry.model_validate(raw)
            )
        except ValidationError:
            continue

    return DeadLetterListResponse(
        count=total,
        items=items,
    )
