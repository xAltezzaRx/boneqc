import unittest

from app.dataset.readiness import (
    DatasetReviewState,
    classify_review_state,
)


class DatasetReadinessTests(
    unittest.TestCase
):
    def test_legacy_overrides_other_state(
        self,
    ):
        result = classify_review_state(
            privacy_group_id=None,
            annotation_count=3,
            draft_consensus_count=1,
            approved_consensus_count=1,
        )

        self.assertEqual(
            result,
            DatasetReviewState.LEGACY,
        )

    def test_approved(self):
        result = classify_review_state(
            privacy_group_id=(
                "pg1_" + ("a" * 64)
            ),
            annotation_count=2,
            draft_consensus_count=0,
            approved_consensus_count=1,
        )

        self.assertEqual(
            result,
            DatasetReviewState.APPROVED,
        )

    def test_draft(self):
        result = classify_review_state(
            privacy_group_id=(
                "pg1_" + ("a" * 64)
            ),
            annotation_count=2,
            draft_consensus_count=1,
            approved_consensus_count=0,
        )

        self.assertEqual(
            result,
            DatasetReviewState
            .CONSENSUS_DRAFT,
        )

    def test_annotated(self):
        result = classify_review_state(
            privacy_group_id=(
                "pg1_" + ("a" * 64)
            ),
            annotation_count=1,
            draft_consensus_count=0,
            approved_consensus_count=0,
        )

        self.assertEqual(
            result,
            DatasetReviewState.ANNOTATED,
        )

    def test_not_annotated(self):
        result = classify_review_state(
            privacy_group_id=(
                "pg1_" + ("a" * 64)
            ),
            annotation_count=0,
            draft_consensus_count=0,
            approved_consensus_count=0,
        )

        self.assertEqual(
            result,
            DatasetReviewState
            .NOT_ANNOTATED,
        )


if __name__ == "__main__":
    unittest.main()
