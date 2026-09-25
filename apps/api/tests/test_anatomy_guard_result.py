import unittest

from app.dicom.anatomy_guard import (
    AnatomyGuardResult,
)
from app.dicom.anatomy_guard_result import (
    build_anatomy_guard_payload,
)


class AnatomyGuardResultTests(
    unittest.TestCase
):
    def test_payload_is_cannot_assess_without_c7(
        self,
    ) -> None:
        anatomy = AnatomyGuardResult(
            supported=False,
            reason=(
                "EXPLICIT_UNSUPPORTED_ANATOMY"
            ),
            evidence={
                "source":
                    "BodyPartExamined",

                "matched_value":
                    "SKULL",

                "matched_hint":
                    "SKULL",
            },
        )

        payload = (
            build_anatomy_guard_payload(
                anatomy
            )
        )

        self.assertEqual(
            payload[
                "final_decision"
            ][
                "status"
            ],
            "CANNOT_ASSESS",
        )

        self.assertEqual(
            payload[
                "quality"
            ][
                "status"
            ],
            "CANNOT_ASSESS",
        )

        self.assertIsNone(
            payload[
                "quality"
            ][
                "anatomical_region"
            ]
        )

        self.assertIsNone(
            payload[
                "quality"
            ][
                "quality_class"
            ]
        )

        self.assertEqual(
            payload[
                "provider"
            ][
                "name"
            ],
            "anatomy_guard",
        )

        self.assertFalse(
            payload[
                "provider_metadata"
            ][
                "c7_invoked"
            ]
        )

        self.assertEqual(
            payload[
                "provider_metadata"
            ][
                "anatomy_reason"
            ],
            "EXPLICIT_UNSUPPORTED_ANATOMY",
        )


if __name__ == "__main__":
    unittest.main()
