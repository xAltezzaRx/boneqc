import unittest

from app.decision.resolver import decision_resolver
from app.models.enums import AnalysisResultStatus
from app.quality.contracts import QualityEvaluation
from app.uncertainty.contracts import UncertaintyEvaluation


def quality(
    status: AnalysisResultStatus,
) -> QualityEvaluation:
    return QualityEvaluation(
        status=status,
        quality_score=0.80,
        engine_version="test",
    )


def uncertainty(
    decision: str,
) -> UncertaintyEvaluation:
    return UncertaintyEvaluation(
        decision=decision,
        minimum_confidence=0.80,
        mean_confidence=0.85,
        engine_version="test",
    )


class FinalDecisionResolverTests(unittest.TestCase):
    def test_pass_accept(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.PASS),
            uncertainty=uncertainty("ACCEPT"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.PASS,
        )

    def test_review_accept(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.REVIEW),
            uncertainty=uncertainty("ACCEPT"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.REVIEW,
        )

    def test_fail_accept(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.FAIL),
            uncertainty=uncertainty("ACCEPT"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.FAIL,
        )

    def test_pass_uncertain_review(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.PASS),
            uncertainty=uncertainty("REVIEW"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.REVIEW,
        )

    def test_fail_uncertain_review(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.FAIL),
            uncertainty=uncertainty("REVIEW"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.REVIEW,
        )

    def test_uncertainty_cannot_assess_overrides(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(AnalysisResultStatus.FAIL),
            uncertainty=uncertainty("CANNOT_ASSESS"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.CANNOT_ASSESS,
        )

    def test_quality_cannot_assess_overrides(self) -> None:
        result = decision_resolver.resolve(
            quality=quality(
                AnalysisResultStatus.CANNOT_ASSESS
            ),
            uncertainty=uncertainty("ACCEPT"),
        )

        self.assertEqual(
            result.status,
            AnalysisResultStatus.CANNOT_ASSESS,
        )


if __name__ == "__main__":
    unittest.main()
