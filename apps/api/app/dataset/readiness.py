from enum import StrEnum


class DatasetReviewState(StrEnum):
    LEGACY = "LEGACY"
    NOT_ANNOTATED = "NOT_ANNOTATED"
    ANNOTATED = "ANNOTATED"
    CONSENSUS_DRAFT = "CONSENSUS_DRAFT"
    APPROVED = "APPROVED"


def classify_review_state(
    *,
    privacy_group_id: str | None,
    annotation_count: int,
    draft_consensus_count: int,
    approved_consensus_count: int,
) -> DatasetReviewState:
    if not privacy_group_id:
        return DatasetReviewState.LEGACY

    if approved_consensus_count > 0:
        return DatasetReviewState.APPROVED

    if draft_consensus_count > 0:
        return DatasetReviewState.CONSENSUS_DRAFT

    if annotation_count > 0:
        return DatasetReviewState.ANNOTATED

    return DatasetReviewState.NOT_ANNOTATED
