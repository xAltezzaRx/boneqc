import unittest
from uuid import uuid4

from app.ml.export import (
    DatasetExportError,
    build_manifest_record,
)
from app.models.enums import (
    AnnotationConsensusStatus,
)
from app.models.study import Study
from app.models.study_annotation_consensus import (
    StudyAnnotationConsensus,
)


def make_study():
    study_id = uuid4()

    return Study(
        id=study_id,
        status="READY",
        privacy_group_id=(
            "pg1_" + ("a" * 64)
        ),
        original_filename=(
            "study.dcm"
        ),
        source_object_key=(
            f"studies/{study_id}/source.dcm"
        ),
        preview_object_key=(
            f"studies/{study_id}/preview.png"
        ),
        dicom_metadata={
            "modality": "DX",
            "rows": 256,
            "columns": 256,
        },
    )


def make_consensus(
    study_id,
    status=(
        AnnotationConsensusStatus.APPROVED
    ),
):
    return StudyAnnotationConsensus(
        id=uuid4(),
        study_id=study_id,
        created_by_user_id=uuid4(),
        reviewed_by_user_id=uuid4(),
        schema_version="0.1",
        status=status,
        source_annotation_ids=[
            str(uuid4()),
            str(uuid4()),
        ],
        labels=[
            {
                "code": "POSITIONING",
                "assessable": True,
                "class_label": (
                    "PROVISIONAL_REVIEW"
                ),
                "confidence": 0.9,
            }
        ],
    )


class DatasetExportTests(
    unittest.TestCase
):
    def test_builds_consensus_record(self):
        study = make_study()

        consensus = make_consensus(
            study.id
        )

        result = (
            build_manifest_record(
                study=study,
                consensus=consensus,
            )
        )

        self.assertEqual(
            result["group_id"],
            study.privacy_group_id,
        )

        self.assertEqual(
            result["labels"][0][
                "source"
            ],
            "CONSENSUS",
        )

        self.assertEqual(
            result["labels"][0][
                "annotator_id"
            ],
            (
                "consensus:"
                + str(consensus.id)
            ),
        )

    def test_rejects_draft_consensus(self):
        study = make_study()

        consensus = make_consensus(
            study.id,
            status=(
                AnnotationConsensusStatus
                .DRAFT
            ),
        )

        with self.assertRaises(
            DatasetExportError
        ):
            build_manifest_record(
                study=study,
                consensus=consensus,
            )

    def test_requires_privacy_group(self):
        study = make_study()

        study.privacy_group_id = None

        consensus = make_consensus(
            study.id
        )

        with self.assertRaises(
            DatasetExportError
        ):
            build_manifest_record(
                study=study,
                consensus=consensus,
            )


if __name__ == "__main__":
    unittest.main()
