import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.annotation import (
    ConsensusCreateRequest,
)


class AnnotationConsensusTests(
    unittest.TestCase
):
    def test_requires_two_sources(self):
        with self.assertRaises(
            ValidationError
        ):
            ConsensusCreateRequest(
                schema_version="0.1",
                source_annotation_ids=[
                    uuid4()
                ],
                labels=[
                    {
                        "code":
                            "POSITIONING",
                        "assessable":
                            True,
                        "class_label":
                            "REVIEW",
                    }
                ],
            )

    def test_rejects_duplicate_sources(self):
        annotation_id = uuid4()

        with self.assertRaises(
            ValidationError
        ):
            ConsensusCreateRequest(
                schema_version="0.1",
                source_annotation_ids=[
                    annotation_id,
                    annotation_id,
                ],
                labels=[
                    {
                        "code":
                            "POSITIONING",
                        "assessable":
                            True,
                        "class_label":
                            "REVIEW",
                    }
                ],
            )

    def test_valid_consensus(self):
        request = (
            ConsensusCreateRequest(
                schema_version="0.1",
                source_annotation_ids=[
                    uuid4(),
                    uuid4(),
                ],
                labels=[
                    {
                        "code":
                            "POSITIONING",
                        "assessable":
                            True,
                        "class_label":
                            "REVIEW",
                        "confidence":
                            0.95,
                    }
                ],
            )
        )

        self.assertEqual(
            len(
                request
                .source_annotation_ids
            ),
            2,
        )


if __name__ == "__main__":
    unittest.main()
