from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.auth.security import (
    require_roles,
)
from app.database.session import (
    get_db_session,
)
from app.dataset.readiness import (
    DatasetReviewState,
    classify_review_state,
)
from app.models.enums import (
    AnnotationConsensusStatus,
    UserRole,
)
from app.models.study import Study
from app.models.study_annotation import (
    StudyAnnotation,
)
from app.models.study_annotation_consensus import (
    StudyAnnotationConsensus,
)
from app.schemas.dataset import (
    DatasetReadinessItem,
    DatasetReadinessResponse,
    DatasetReadinessSummary,
)


router = APIRouter(
    prefix="/dataset",
    tags=["dataset"],
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.DOCTOR,
            )
        )
    ],
)


@router.get(
    "/readiness",
    response_model=(
        DatasetReadinessResponse
    ),
)
async def get_dataset_readiness(
    state: DatasetReviewState | None = Query(
        default=None
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DatasetReadinessResponse:
    annotation_count = (
        select(
            func.count(
                StudyAnnotation.id
            )
        )
        .where(
            StudyAnnotation.study_id
            == Study.id
        )
        .correlate(Study)
        .scalar_subquery()
    )

    consensus_count = (
        select(
            func.count(
                StudyAnnotationConsensus.id
            )
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == Study.id
        )
        .correlate(Study)
        .scalar_subquery()
    )

    draft_consensus_count = (
        select(
            func.count(
                StudyAnnotationConsensus.id
            )
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == Study.id,
            StudyAnnotationConsensus
            .status
            == AnnotationConsensusStatus
            .DRAFT,
        )
        .correlate(Study)
        .scalar_subquery()
    )

    approved_consensus_count = (
        select(
            func.count(
                StudyAnnotationConsensus.id
            )
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == Study.id,
            StudyAnnotationConsensus
            .status
            == AnnotationConsensusStatus
            .APPROVED,
        )
        .correlate(Study)
        .scalar_subquery()
    )

    approved_consensus_id = (
        select(
            StudyAnnotationConsensus.id
        )
        .where(
            StudyAnnotationConsensus
            .study_id
            == Study.id,
            StudyAnnotationConsensus
            .status
            == AnnotationConsensusStatus
            .APPROVED,
        )
        .order_by(
            StudyAnnotationConsensus
            .created_at.desc()
        )
        .limit(1)
        .correlate(Study)
        .scalar_subquery()
    )

    result = await session.execute(
        select(
            Study,
            annotation_count.label(
                "annotation_count"
            ),
            consensus_count.label(
                "consensus_count"
            ),
            draft_consensus_count.label(
                "draft_consensus_count"
            ),
            approved_consensus_count.label(
                "approved_consensus_count"
            ),
            approved_consensus_id.label(
                "approved_consensus_id"
            ),
        )
        .order_by(
            Study.created_at.desc()
        )
    )

    items: list[
        DatasetReadinessItem
    ] = []

    summary_counts = {
        DatasetReviewState.LEGACY: 0,
        DatasetReviewState.NOT_ANNOTATED: 0,
        DatasetReviewState.ANNOTATED: 0,
        DatasetReviewState.CONSENSUS_DRAFT: 0,
        DatasetReviewState.APPROVED: 0,
    }

    privacy_ready = 0

    for row in result.all():
        study = row[0]

        annotation_total = int(
            row.annotation_count or 0
        )

        consensus_total = int(
            row.consensus_count or 0
        )

        draft_total = int(
            row.draft_consensus_count
            or 0
        )

        approved_total = int(
            row.approved_consensus_count
            or 0
        )

        review_state = (
            classify_review_state(
                privacy_group_id=(
                    study.privacy_group_id
                ),
                annotation_count=(
                    annotation_total
                ),
                draft_consensus_count=(
                    draft_total
                ),
                approved_consensus_count=(
                    approved_total
                ),
            )
        )

        summary_counts[
            review_state
        ] += 1

        is_privacy_ready = (
            study.privacy_group_id
            is not None
        )

        if is_privacy_ready:
            privacy_ready += 1

        modality = (
            dict(
                study.dicom_metadata
                or {}
            ).get("modality")
        )

        item = DatasetReadinessItem(
            id=study.id,
            study_status=study.status,
            modality=(
                str(modality)
                if modality is not None
                else None
            ),
            created_at=study.created_at,
            privacy_group_id=(
                study.privacy_group_id
            ),
            privacy_ready=(
                is_privacy_ready
            ),
            review_state=(
                review_state
            ),
            annotation_count=(
                annotation_total
            ),
            consensus_count=(
                consensus_total
            ),
            draft_consensus_count=(
                draft_total
            ),
            approved_consensus_id=(
                row.approved_consensus_id
            ),
            eligible_for_dataset=(
                review_state
                == DatasetReviewState
                .APPROVED
            ),
        )

        items.append(item)

    total_studies = len(items)

    summary = (
        DatasetReadinessSummary(
            total_studies=(
                total_studies
            ),
            privacy_ready=(
                privacy_ready
            ),
            legacy=(
                summary_counts[
                    DatasetReviewState
                    .LEGACY
                ]
            ),
            not_annotated=(
                summary_counts[
                    DatasetReviewState
                    .NOT_ANNOTATED
                ]
            ),
            annotated=(
                summary_counts[
                    DatasetReviewState
                    .ANNOTATED
                ]
            ),
            consensus_draft=(
                summary_counts[
                    DatasetReviewState
                    .CONSENSUS_DRAFT
                ]
            ),
            approved=(
                summary_counts[
                    DatasetReviewState
                    .APPROVED
                ]
            ),
            eligible_for_dataset=(
                summary_counts[
                    DatasetReviewState
                    .APPROVED
                ]
            ),
        )
    )

    if state is not None:
        filtered = [
            item
            for item in items
            if item.review_state
            == state
        ]
    else:
        filtered = items

    filtered_total = len(
        filtered
    )

    paged = filtered[
        offset:offset + limit
    ]

    return DatasetReadinessResponse(
        summary=summary,
        items=paged,
        total=filtered_total,
        limit=limit,
        offset=offset,
        state_filter=state,
    )
