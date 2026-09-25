import unittest

from app.ai.contracts import (
    AIAnalysisResponse,
    QualityObservation,
)
from app.models.enums import AnalysisResultStatus
from app.quality.engine import quality_engine


def response(
    observations: list[QualityObservation],
) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        provider_name="test",
        provider_version="1.0",
        summary="Quality engine unit test",
        observations=observations,
        metadata={"test": True},
    )


class QualityEngineTests(unittest.TestCase):
    def test_pass(self) -> None:
        result = quality_engine.evaluate(
            response([
                QualityObservation(
                    code="POSITIONING",
                    score=0.90,
                    confidence=0.95,
                    message="ok",
                ),
                QualityObservation(
                    code="ROI_PLACEMENT",
                    score=0.85,
                    confidence=0.90,
                    message="ok",
                ),
                QualityObservation(
                    code="ARTIFACTS",
                    score=0.88,
                    confidence=0.92,
                    message="ok",
                ),
            ])
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.PASS,
        )
        self.assertEqual(len(result.violations), 0)
        self.assertAlmostEqual(
            result.quality_score,
            0.8767,
            places=4,
        )

    def test_review(self) -> None:
        result = quality_engine.evaluate(
            response([
                QualityObservation(
                    code="POSITIONING",
                    score=0.91,
                    confidence=0.91,
                    message="ok",
                ),
                QualityObservation(
                    code="ROI_PLACEMENT",
                    score=0.72,
                    confidence=0.72,
                    message="review",
                ),
                QualityObservation(
                    code="ARTIFACTS",
                    score=0.88,
                    confidence=0.88,
                    message="ok",
                ),
            ])
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.REVIEW,
        )
        self.assertEqual(len(result.violations), 1)
        self.assertEqual(
            result.violations[0].code,
            "ROI_PLACEMENT",
        )
        self.assertEqual(
            result.violations[0].severity,
            AnalysisResultStatus.REVIEW,
        )

    def test_fail(self) -> None:
        result = quality_engine.evaluate(
            response([
                QualityObservation(
                    code="POSITIONING",
                    score=0.92,
                    confidence=0.94,
                    message="ok",
                ),
                QualityObservation(
                    code="ROI_PLACEMENT",
                    score=0.31,
                    confidence=0.90,
                    message="fail",
                ),
                QualityObservation(
                    code="ARTIFACTS",
                    score=0.86,
                    confidence=0.89,
                    message="ok",
                ),
            ])
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.FAIL,
        )

        self.assertTrue(
            any(
                violation.severity
                == AnalysisResultStatus.FAIL
                for violation in result.violations
            )
        )

    def test_cannot_assess(self) -> None:
        result = quality_engine.evaluate(
            response([
                QualityObservation(
                    code="POSITIONING",
                    score=0.90,
                    confidence=0.91,
                    message="ok",
                ),
                QualityObservation(
                    code="ROI_PLACEMENT",
                    score=None,
                    confidence=0.20,
                    assessable=False,
                    message="cannot assess",
                ),
                QualityObservation(
                    code="ARTIFACTS",
                    score=0.88,
                    confidence=0.90,
                    message="ok",
                ),
            ])
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.CANNOT_ASSESS,
        )
        self.assertIsNone(result.quality_score)


if __name__ == "__main__":
    unittest.main()
