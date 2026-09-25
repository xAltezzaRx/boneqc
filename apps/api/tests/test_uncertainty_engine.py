import unittest

from app.ai.contracts import (
    AIAnalysisResponse,
    QualityObservation,
)
from app.uncertainty.engine import uncertainty_engine


def response(
    observations: list[QualityObservation],
) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        provider_name="test",
        provider_version="1.0",
        summary="Uncertainty engine unit test",
        observations=observations,
    )


class UncertaintyEngineTests(unittest.TestCase):
    def test_accept(self) -> None:
        result = uncertainty_engine.evaluate(
            response([
                QualityObservation(
                    code="A",
                    score=0.90,
                    confidence=0.91,
                    message="ok",
                ),
                QualityObservation(
                    code="B",
                    score=0.85,
                    confidence=0.82,
                    message="ok",
                ),
            ])
        )

        self.assertEqual(result.decision, "ACCEPT")
        self.assertEqual(result.minimum_confidence, 0.82)
        self.assertAlmostEqual(
            result.mean_confidence,
            0.865,
            places=4,
        )

    def test_review(self) -> None:
        result = uncertainty_engine.evaluate(
            response([
                QualityObservation(
                    code="A",
                    score=0.90,
                    confidence=0.90,
                    message="ok",
                ),
                QualityObservation(
                    code="B",
                    score=0.85,
                    confidence=0.64,
                    message="uncertain",
                ),
            ])
        )

        self.assertEqual(result.decision, "REVIEW")
        self.assertEqual(result.minimum_confidence, 0.64)

    def test_cannot_assess_low_confidence(self) -> None:
        result = uncertainty_engine.evaluate(
            response([
                QualityObservation(
                    code="A",
                    score=0.90,
                    confidence=0.92,
                    message="ok",
                ),
                QualityObservation(
                    code="B",
                    score=0.85,
                    confidence=0.31,
                    message="too uncertain",
                ),
            ])
        )

        self.assertEqual(
            result.decision,
            "CANNOT_ASSESS",
        )
        self.assertEqual(
            result.minimum_confidence,
            0.31,
        )

    def test_cannot_assess_missing_confidence(self) -> None:
        result = uncertainty_engine.evaluate(
            response([
                QualityObservation(
                    code="A",
                    score=0.90,
                    confidence=None,
                    message="missing confidence",
                )
            ])
        )

        self.assertEqual(
            result.decision,
            "CANNOT_ASSESS",
        )

    def test_cannot_assess_unassessable(self) -> None:
        result = uncertainty_engine.evaluate(
            response([
                QualityObservation(
                    code="A",
                    score=None,
                    confidence=0.90,
                    assessable=False,
                    message="not assessable",
                )
            ])
        )

        self.assertEqual(
            result.decision,
            "CANNOT_ASSESS",
        )


if __name__ == "__main__":
    unittest.main()
