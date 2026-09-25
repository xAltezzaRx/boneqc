from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import (
    create_audit_event,
)
from app.auth.security import require_roles
from app.database.session import (
    get_db_session,
)
from app.models.enums import (
    AnnotationConsensusStatus,
    AuditEventType,
    UserRole,
)
from app.models.study import Study
from app.models.study_annotation import (
    StudyAnnotation,
)
from app.models.study_annotation_consensus import (
    StudyAnnotationConsensus,
)
from app.models.user import User
from app.schemas.annotation import (
    AnnotationCreateRequest,
    ConsensusCreateRequest,
    MyAnnotationStatusResponse,
    StudyAnnotationConsensusListResponse,
    StudyAnnotationConsensusResponse,
    StudyAnnotationListResponse,
    StudyAnnotationResponse,
)


router = APIRouter(
    prefix="/studies",
    tags=["annotations"],
)


Reviewer = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.DOCTOR,
        )
    ),
]


async def require_study(
    session: AsyncSession,
    study_id: UUID,
) -> Study:
    study = await session.get(
        Study,
        study_id,
    )

    if study is None:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail={
                "code": "STUDY_NOT_FOUND",
            },
        )

    return study


@router.post(
    "/{study_id}/annotations",
    response_model=StudyAnnotationResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_annotation(
    study_id: UUID,
    request: AnnotationCreateRequest,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationResponse:
    await require_study(
        session,
        study_id,
    )

    annotation = StudyAnnotation(
        study_id=study_id,
        reviewer_user_id=current_user.id,
        schema_version=(
            request.schema_version
        ),
        labels=[
            label.model_dump(
                mode="json"
            )
            for label in request.labels
        ],
    )

    session.add(annotation)

    try:
        await session.flush()

        await create_audit_event(
            session,
            event_type=(
                AuditEventType
                .ANNOTATION_CREATED
            ),
            entity_type=(
                "STUDY_ANNOTATION"
            ),
            entity_id=annotation.id,
            study_id=study_id,
            payload={
                "annotation_id": str(
                    annotation.id
                ),
                "schema_version": (
                    annotation
                    .schema_version
                ),
                "label_count": len(
                    annotation.labels
                ),
                "reviewer_user_id": str(
                    current_user.id
                ),
            },
        )

        await session.commit()

        await session.refresh(
            annotation
        )

    except SQLAlchemyError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail={
                "code":
                    "DATABASE_UNAVAILABLE",
            },
        ) from exc

    return (
        StudyAnnotationResponse
        .model_validate(annotation)
    )


@router.get(
    "/{study_id}/annotations",
    response_model=(
        StudyAnnotationListResponse
    ),
)
async def list_annotations(
    study_id: UUID,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationListResponse:
    await require_study(
        session,
        study_id,
    )

    total = await session.scalar(
        select(func.count())
        .select_from(
            StudyAnnotation
        )
        .where(
            StudyAnnotation.study_id
            == study_id
        )
    )

    rows = await session.scalars(
        select(StudyAnnotation)
        .where(
            StudyAnnotation.study_id
            == study_id
        )
        .order_by(
            StudyAnnotation
            .created_at.asc()
        )
    )

    return StudyAnnotationListResponse(
        items=[
            StudyAnnotationResponse
            .model_validate(item)
            for item in rows
        ],
        total=int(total or 0),
    )


@router.get(
    "/{study_id}/my-annotation-status",
    response_model=(
        MyAnnotationStatusResponse
    ),
)
async def get_my_annotation_status(
    study_id: UUID,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> MyAnnotationStatusResponse:
    await require_study(
        session,
        study_id,
    )

    annotation_id = await session.scalar(
        select(
            StudyAnnotation.id
        )
        .where(
            StudyAnnotation.study_id
            == study_id,
            StudyAnnotation.reviewer_user_id
            == current_user.id,
        )
        .limit(1)
    )

    return MyAnnotationStatusResponse(
        reviewed=(
            annotation_id is not None
        )
    )


@router.post(
    "/{study_id}/consensus",
    response_model=(
        StudyAnnotationConsensusResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
async def create_consensus(
    study_id: UUID,
    request: ConsensusCreateRequest,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationConsensusResponse:
    await require_study(
        session,
        study_id,
    )

    source_ids = list(
        request.source_annotation_ids
    )

    rows = list(
        (
            await session.scalars(
                select(
                    StudyAnnotation
                ).where(
                    StudyAnnotation.id.in_(
                        source_ids
                    )
                )
            )
        ).all()
    )

    if len(rows) != len(source_ids):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code":
                    "ANNOTATION_SOURCE_NOT_FOUND",
            },
        )

    if any(
        item.study_id != study_id
        for item in rows
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code":
                    "ANNOTATION_SOURCE_STUDY_MISMATCH",
            },
        )

    if any(
        item.schema_version
        != request.schema_version
        for item in rows
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code":
                    "ANNOTATION_SCHEMA_MISMATCH",
            },
        )

    reviewer_ids = {
        item.reviewer_user_id
        for item in rows
        if item.reviewer_user_id
        is not None
    }

    if len(reviewer_ids) < 2:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={
                "code":
                    "CONSENSUS_REQUIRES_TWO_REVIEWERS",
            },
        )

    consensus = StudyAnnotationConsensus(
        study_id=study_id,
        created_by_user_id=(
            current_user.id
        ),
        reviewed_by_user_id=None,
        schema_version=(
            request.schema_version
        ),
        status=(
            AnnotationConsensusStatus.DRAFT
        ),
        source_annotation_ids=[
            str(item)
            for item in source_ids
        ],
        labels=[
            label.model_dump(
                mode="json"
            )
            for label in request.labels
        ],
        reviewed_at=None,
    )

    session.add(consensus)

    try:
        await session.flush()

        await create_audit_event(
            session,
            event_type=(
                AuditEventType
                .CONSENSUS_CREATED
            ),
            entity_type=(
                "STUDY_ANNOTATION_CONSENSUS"
            ),
            entity_id=consensus.id,
            study_id=study_id,
            payload={
                "consensus_id": str(
                    consensus.id
                ),
                "schema_version": (
                    consensus
                    .schema_version
                ),
                "source_annotation_ids": (
                    consensus
                    .source_annotation_ids
                ),
                "label_count": len(
                    consensus.labels
                ),
            },
        )

        await session.commit()

        await session.refresh(
            consensus
        )

    except SQLAlchemyError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_503_SERVICE_UNAVAILABLE
            ),
            detail={
                "code":
                    "DATABASE_UNAVAILABLE",
            },
        ) from exc

    return (
        StudyAnnotationConsensusResponse
        .model_validate(consensus)
    )


@router.get(
    "/{study_id}/consensus",
    response_model=(
        StudyAnnotationConsensusListResponse
    ),
)
async def list_consensus(
    study_id: UUID,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationConsensusListResponse:
    await require_study(
        session,
        study_id,
    )

    total = await session.scalar(
        select(func.count())
        .select_from(
            StudyAnnotationConsensus
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == study_id
        )
    )

    rows = await session.scalars(
        select(
            StudyAnnotationConsensus
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == study_id
        )
        .order_by(
            StudyAnnotationConsensus
            .created_at.asc()
        )
    )

    return (
        StudyAnnotationConsensusListResponse(
            items=[
                StudyAnnotationConsensusResponse
                .model_validate(item)
                for item in rows
            ],
            total=int(total or 0),
        )
    )


async def get_consensus_for_action(
    *,
    session: AsyncSession,
    study_id: UUID,
    consensus_id: UUID,
) -> StudyAnnotationConsensus:
    await require_study(
        session,
        study_id,
    )

    consensus = await session.get(
        StudyAnnotationConsensus,
        consensus_id,
    )

    if (
        consensus is None
        or consensus.study_id
        != study_id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail={
                "code":
                    "CONSENSUS_NOT_FOUND",
            },
        )

    return consensus


@router.post(
    "/{study_id}/consensus/"
    "{consensus_id}/approve",
    response_model=(
        StudyAnnotationConsensusResponse
    ),
)
async def approve_consensus(
    study_id: UUID,
    consensus_id: UUID,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationConsensusResponse:
    consensus = (
        await get_consensus_for_action(
            session=session,
            study_id=study_id,
            consensus_id=consensus_id,
        )
    )

    if (
        consensus.status
        != AnnotationConsensusStatus.DRAFT
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "CONSENSUS_NOT_DRAFT",
            },
        )

    if (
        consensus.created_by_user_id
        == current_user.id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "CONSENSUS_REQUIRES_INDEPENDENT_APPROVER",
            },
        )

    existing = await session.scalar(
        select(
            StudyAnnotationConsensus
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == study_id,
            StudyAnnotationConsensus
            .status
            == AnnotationConsensusStatus
            .APPROVED,
        )
        .limit(1)
    )

    if existing is not None:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "APPROVED_CONSENSUS_ALREADY_EXISTS",
                "consensus_id": str(
                    existing.id
                ),
            },
        )

    consensus.status = (
        AnnotationConsensusStatus.APPROVED
    )

    consensus.reviewed_by_user_id = (
        current_user.id
    )

    consensus.reviewed_at = (
        datetime.now(timezone.utc)
    )

    await create_audit_event(
        session,
        event_type=(
            AuditEventType
            .CONSENSUS_APPROVED
        ),
        entity_type=(
            "STUDY_ANNOTATION_CONSENSUS"
        ),
        entity_id=consensus.id,
        study_id=study_id,
        payload={
            "consensus_id": str(
                consensus.id
            ),
            "source_annotation_ids": (
                consensus
                .source_annotation_ids
            ),
            "label_count": len(
                consensus.labels
            ),
        },
    )

    await session.commit()

    await session.refresh(
        consensus
    )

    return (
        StudyAnnotationConsensusResponse
        .model_validate(consensus)
    )


@router.post(
    "/{study_id}/consensus/"
    "{consensus_id}/reject",
    response_model=(
        StudyAnnotationConsensusResponse
    ),
)
async def reject_consensus(
    study_id: UUID,
    consensus_id: UUID,
    current_user: Reviewer,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> StudyAnnotationConsensusResponse:
    consensus = (
        await get_consensus_for_action(
            session=session,
            study_id=study_id,
            consensus_id=consensus_id,
        )
    )

    if (
        consensus.status
        != AnnotationConsensusStatus.DRAFT
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "CONSENSUS_NOT_DRAFT",
            },
        )

    if (
        consensus.created_by_user_id
        == current_user.id
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail={
                "code":
                    "CONSENSUS_REQUIRES_INDEPENDENT_REVIEWER",
            },
        )

    consensus.status = (
        AnnotationConsensusStatus.REJECTED
    )

    consensus.reviewed_by_user_id = (
        current_user.id
    )

    consensus.reviewed_at = (
        datetime.now(timezone.utc)
    )

    await create_audit_event(
        session,
        event_type=(
            AuditEventType
            .CONSENSUS_REJECTED
        ),
        entity_type=(
            "STUDY_ANNOTATION_CONSENSUS"
        ),
        entity_id=consensus.id,
        study_id=study_id,
        payload={
            "consensus_id": str(
                consensus.id
            ),
        },
    )

    await session.commit()

    await session.refresh(
        consensus
    )

    return (
        StudyAnnotationConsensusResponse
        .model_validate(consensus)
    )
