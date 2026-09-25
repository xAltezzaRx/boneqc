from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import require_roles
from app.models.enums import UserRole
from app.database.session import get_db_session
from app.models.audit_event import AuditEvent
from app.models.study import Study
from app.schemas.audit import (
    AuditEventResponse,
    AuditTimelineResponse,
)


router = APIRouter(
    prefix="/studies",
    tags=["audit"],
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.DOCTOR))],
)


@router.get(
    "/{study_id}/audit",
    response_model=AuditTimelineResponse,
)
async def get_study_audit(
    study_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AuditTimelineResponse:

    study = await session.get(
        Study,
        study_id,
    )

    if study is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "STUDY_NOT_FOUND",
            },
        )

    result = await session.execute(
        select(AuditEvent)
        .where(
            AuditEvent.study_id == study_id
        )
        .order_by(
            AuditEvent.created_at.asc()
        )
    )

    events = result.scalars().all()

    return AuditTimelineResponse(
        study_id=study_id,
        events=[
            AuditEventResponse.model_validate(event)
            for event in events
        ],
    )
