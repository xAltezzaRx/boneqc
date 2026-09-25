import unittest

import numpy as np

from app.dicom.input_sanity import (
    evaluate_pixels,
)


class InputSanityTests(
    unittest.TestCase
):
    def test_black_is_rejected(
        self,
    ) -> None:
        pixels = np.zeros(
            (320, 280),
            dtype=np.uint8,
        )

        result = evaluate_pixels(
            pixels
        )

        self.assertFalse(
            result.assessable
        )

        self.assertEqual(
            result.reason,
            "DEGENERATE_UNIFORM_PIXELS",
        )

    def test_white_is_rejected(
        self,
    ) -> None:
        pixels = np.full(
            (320, 280),
            255,
            dtype=np.uint8,
        )

        result = evaluate_pixels(
            pixels
        )

        self.assertFalse(
            result.assessable
        )

        self.assertEqual(
            result.reason,
            "DEGENERATE_UNIFORM_PIXELS",
        )

    def test_seeded_random_noise_is_rejected(
        self,
    ) -> None:
        rng = (
            np.random
            .default_rng(
                20260923
            )
        )

        pixels = rng.integers(
            0,
            256,
            size=(320, 280),
            dtype=np.uint8,
        )

        result = evaluate_pixels(
            pixels
        )

        self.assertFalse(
            result.assessable
        )

        self.assertEqual(
            result.reason,
            "SYNTHETIC_NOISE_PATTERN",
        )

        self.assertGreaterEqual(
            result.metrics[
                "entropy"
            ],
            7.5,
        )

        self.assertGreaterEqual(
            result.metrics[
                "zlib_ratio"
            ],
            0.90,
        )

    def test_structured_gradient_is_accepted(
        self,
    ) -> None:
        x = np.linspace(
            0,
            255,
            280,
            dtype=np.uint8,
        )

        pixels = np.tile(
            x,
            (320, 1),
        )

        result = evaluate_pixels(
            pixels
        )

        self.assertTrue(
            result.assessable
        )

        self.assertIsNone(
            result.reason
        )

    def test_large_occlusion_does_not_mean_noise(
        self,
    ) -> None:
        x = np.linspace(
            0,
            255,
            280,
            dtype=np.uint8,
        )

        pixels = np.tile(
            x,
            (320, 1),
        )

        pixels[
            80:240,
            56:224,
        ] = 0

        result = evaluate_pixels(
            pixels
        )

        self.assertTrue(
            result.assessable
        )

        self.assertIsNone(
            result.reason
        )


if __name__ == "__main__":
    unittest.main()


class InputSanityResultContractTests(
    unittest.TestCase
):
    def test_cannot_assess_payload_does_not_claim_c7(
        self,
    ) -> None:
        from app.dicom.input_sanity import (
            InputSanityResult,
        )
        from app.dicom.input_sanity_result import (
            build_input_sanity_payload,
        )

        sanity = InputSanityResult(
            assessable=False,
            reason=(
                "SYNTHETIC_NOISE_PATTERN"
            ),
            metrics={
                "entropy": 7.96,
                "zlib_ratio": 0.998,
            },
        )

        payload = (
            build_input_sanity_payload(
                sanity
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
                "quality_class"
            ]
        )

        self.assertIsNone(
            payload[
                "quality"
            ][
                "anatomical_region"
            ]
        )

        self.assertEqual(
            payload[
                "provider"
            ][
                "name"
            ],
            "input_sanity_gate",
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
                "sanity_reason"
            ],
            "SYNTHETIC_NOISE_PATTERN",
        )
