from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.models.model_version import ModelVersion
from app.schemas.model_version import (
    ModelVersionListResponse,
    ModelVersionResponse,
)

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get(
    "",
    response_model=ModelVersionListResponse,
)
async def list_model_versions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> ModelVersionListResponse:
    total = await session.scalar(
        select(func.count()).select_from(ModelVersion)
    )

    result = await session.execute(
        select(ModelVersion)
        .order_by(
            ModelVersion.name,
            ModelVersion.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    models = result.scalars().all()

    return ModelVersionListResponse(
        items=[
            ModelVersionResponse.model_validate(model)
            for model in models
        ],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{model_version_id}",
    response_model=ModelVersionResponse,
)
async def get_model_version(
    model_version_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ModelVersionResponse:
    model = await session.get(
        ModelVersion,
        model_version_id,
    )

    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "MODEL_VERSION_NOT_FOUND",
            },
        )

    return ModelVersionResponse.model_validate(model)
