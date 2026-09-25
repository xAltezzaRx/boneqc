from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.dataset.readiness import (
    DatasetReviewState,
)
from app.models.enums import StudyStatus


class DatasetReadinessSummary(BaseModel):
    total_studies: int

    privacy_ready: int
    legacy: int

    not_annotated: int
    annotated: int
    consensus_draft: int
    approved: int

    eligible_for_dataset: int


class DatasetReadinessItem(BaseModel):
    id: UUID

    study_status: StudyStatus

    modality: str | None
    created_at: datetime

    privacy_group_id: str | None
    privacy_ready: bool

    review_state: DatasetReviewState

    annotation_count: int
    consensus_count: int
    draft_consensus_count: int

    approved_consensus_id: UUID | None

    eligible_for_dataset: bool


class DatasetReadinessResponse(BaseModel):
    summary: DatasetReadinessSummary

    items: list[
        DatasetReadinessItem
    ]

    total: int
    limit: int
    offset: int

    state_filter: (
        DatasetReviewState
        | None
    )
