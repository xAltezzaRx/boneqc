import unittest

from pydicom.dataset import (
    Dataset,
)
from pydicom.sequence import (
    Sequence,
)

from app.dicom.anatomy_guard import (
    evaluate_dataset,
)


class AnatomyGuardTests(
    unittest.TestCase
):
    def test_empty_metadata_is_not_rejected(
        self,
    ) -> None:
        ds = Dataset()

        result = evaluate_dataset(
            ds
        )

        self.assertTrue(
            result.supported
        )

        self.assertIsNone(
            result.reason
        )

    def test_empty_body_part_is_not_rejected(
        self,
    ) -> None:
        ds = Dataset()
        ds.BodyPartExamined = ""

        result = evaluate_dataset(
            ds
        )

        self.assertTrue(
            result.supported
        )

    def test_lumbar_spine_is_supported(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "LUMBAR SPINE"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertTrue(
            result.supported
        )

        self.assertIsNone(
            result.reason
        )

    def test_hip_is_supported(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "LEFT HIP"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertTrue(
            result.supported
        )

    def test_proximal_femur_is_supported(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "PROXIMAL FEMUR"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertTrue(
            result.supported
        )

    def test_skull_body_part_is_rejected(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "SKULL"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertFalse(
            result.supported
        )

        self.assertEqual(
            result.reason,
            (
                "EXPLICIT_UNSUPPORTED_ANATOMY"
            ),
        )

        self.assertEqual(
            result.evidence[
                "matched_hint"
            ],
            "SKULL",
        )

    def test_skull_sequence_is_rejected(
        self,
    ) -> None:
        ds = Dataset()

        region = Dataset()

        region.CodeValue = (
            "89545001"
        )

        region.CodingSchemeDesignator = (
            "SCT"
        )

        region.CodeMeaning = (
            "Skull"
        )

        ds.AnatomicRegionSequence = (
            Sequence(
                [region]
            )
        )

        result = evaluate_dataset(
            ds
        )

        self.assertFalse(
            result.supported
        )

        self.assertEqual(
            result.reason,
            (
                "EXPLICIT_UNSUPPORTED_ANATOMY"
            ),
        )

    def test_chest_is_rejected(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "CHEST"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertFalse(
            result.supported
        )

    def test_forearm_is_rejected(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "FOREARM"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertFalse(
            result.supported
        )

    def test_cervical_spine_is_rejected(
        self,
    ) -> None:
        ds = Dataset()

        ds.BodyPartExamined = (
            "CERVICAL SPINE"
        )

        result = evaluate_dataset(
            ds
        )

        self.assertFalse(
            result.supported
        )


if __name__ == "__main__":
    unittest.main()
